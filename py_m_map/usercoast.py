"""
User-supplied coastline drawing.

m_usercoast — ported from m_usercoast.m / mu_coast.m (the 'user' branch).

Supports:
  * MATLAB .mat files with 'ncst' (Nx2 lon/lat with NaN-row separators)
    and optionally 'Area' (polygon areas; positive = land, negative = lake)
  * Shapefiles / GeoJSON (via cartopy shapereader)
  * Raw Nx2 arrays passed directly as the first argument
"""
from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt

from .projection import m_ll2xy
from ._state import get_state
from .coast import _densify_ring


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def m_usercoast(source, style: str = 'line', *args, **kwargs) -> None:
    """
    Draw a user-supplied coastline on the current map.

    Parameters
    ----------
    source : str or array-like
        One of:
        * Path to a MATLAB ``.mat`` file containing ``ncst`` (Nx2 float array,
          NaN-row separators between polygon rings) and optionally ``Area``
          (polygon area per ring; positive = land, negative = lake/hole).
        * Path to a shapefile (``.shp``) or GeoJSON (``.geojson``).
        * A Nx2 NumPy array in the same ``ncst`` NaN-separated format.
    style : {'line', 'patch', 'speckle'}
        Drawing style.  Default ``'line'``.
    *args
        Optional positional colour argument (MATLAB compatibility).
        E.g. ``m_usercoast('coast.mat', 'patch', 'g')`` sets facecolor='g'.
    **kwargs
        Forwarded to the drawing primitive (``ax.plot``, ``ax.fill``, or
        ``m_hatch``).  Common keys: ``color``, ``facecolor``, ``edgecolor``,
        ``linewidth``.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    color_arg = args[0] if args else None

    # --- load geometry -------------------------------------------------------
    if isinstance(source, str):
        if source.lower().endswith(('.shp', '.geojson', '.json')):
            ncst, areas = _load_shapefile(source)
        else:
            # Default: attempt MATLAB .mat (works with or without extension)
            try:
                ncst, areas = _load_mat(source)
            except Exception as exc:
                try:
                    ncst, areas = _load_shapefile(source)
                except Exception:
                    raise IOError(
                        f"Could not load '{source}' as .mat or shapefile"
                    ) from exc
    else:
        ncst = np.asarray(source, dtype=float)
        if ncst.ndim == 1:
            ncst = ncst.reshape(-1, 2)
        areas = None

    segments, seg_areas = _parse_ncst(ncst, areas)

    # --- dispatch to drawing mode --------------------------------------------
    if style in ('patch', 'fill'):
        _draw_patch(segments, seg_areas, color_arg, state, **kwargs)
    elif style == 'speckle':
        _draw_speckle(segments, color_arg, state, **kwargs)
    else:
        _draw_line(segments, color_arg, state, **kwargs)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _load_mat(filename: str):
    """Load ncst and Area from a MATLAB .mat file."""
    try:
        import scipy.io
        data = scipy.io.loadmat(filename)
    except ImportError as exc:
        raise ImportError("scipy is required to read .mat files") from exc
    except Exception as exc:
        raise IOError(f"Could not load '{filename}': {exc}") from exc

    if 'ncst' not in data:
        raise ValueError(f"No 'ncst' variable found in '{filename}'")

    ncst = np.asarray(data['ncst'], dtype=float)
    if ncst.ndim > 2:
        ncst = ncst.squeeze()

    areas = None
    for key in ('Area', 'area', 'AREA'):
        if key in data:
            areas = np.asarray(data[key], dtype=float).ravel()
            break

    return ncst, areas


def _load_shapefile(filename: str):
    """
    Load geometry from a shapefile or GeoJSON into ncst / areas format.

    Uses cartopy's shapereader (already a project dependency).  Polygon
    exterior rings are concatenated with NaN-row separators; Area is set
    to the signed area (positive for land polygons, negative for holes).
    """
    try:
        from cartopy.io.shapereader import Reader
    except ImportError as exc:
        raise ImportError("cartopy is required to read shapefiles") from exc

    rows_lon: list[float] = []
    rows_lat: list[float] = []
    areas: list[float] = []

    try:
        geoms = list(Reader(filename).geometries())
    except Exception as exc:
        raise IOError(f"Could not read shapefile '{filename}': {exc}") from exc

    for geom in geoms:
        if geom.geom_type in ('MultiPolygon', 'Polygon'):
            parts = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
            for poly in parts:
                if poly.geom_type != 'Polygon':
                    continue
                coords = np.asarray(list(poly.exterior.coords), dtype=float)
                if len(coords) < 3:
                    continue
                rows_lon.extend(coords[:, 0])
                rows_lat.extend(coords[:, 1])
                rows_lon.append(np.nan)
                rows_lat.append(np.nan)
                areas.append(abs(poly.area))  # positive = land
        elif geom.geom_type in ('MultiLineString', 'LineString'):
            lines = list(geom.geoms) if geom.geom_type == 'MultiLineString' else [geom]
            for line in lines:
                coords = np.asarray(list(line.coords), dtype=float)
                if len(coords) < 2:
                    continue
                rows_lon.extend(coords[:, 0])
                rows_lat.extend(coords[:, 1])
                rows_lon.append(np.nan)
                rows_lat.append(np.nan)
                areas.append(1.0)

    if not rows_lon:
        return np.zeros((0, 2), dtype=float), np.zeros(0, dtype=float)

    ncst = np.column_stack([rows_lon, rows_lat])
    return ncst, np.asarray(areas, dtype=float)


# ---------------------------------------------------------------------------
# Segment parsing
# ---------------------------------------------------------------------------

def _parse_ncst(ncst: np.ndarray, areas=None):
    """
    Split an ncst array (NaN rows as separators) into per-ring arrays.

    Returns
    -------
    segments : list of (lon_array, lat_array)
    seg_areas : list of float  — area per segment (1.0 if not provided)
    """
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    n = len(ncst)
    start = 0

    for i in range(n + 1):
        at_end = (i == n)
        at_nan = (not at_end) and (np.isnan(ncst[i, 0]) or np.isnan(ncst[i, 1]))

        if at_nan or at_end:
            if i > start:
                seg = ncst[start:i]
                if len(seg) >= 2:
                    segments.append((seg[:, 0].copy(), seg[:, 1].copy()))
            start = i + 1

    if areas is not None:
        af = np.asarray(areas, dtype=float).ravel()
        seg_areas = [
            float(af[i]) if i < len(af) else 1.0
            for i in range(len(segments))
        ]
    else:
        seg_areas = [1.0] * len(segments)

    return segments, seg_areas


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _draw_line(segments, color_arg, state, **kwargs) -> None:
    """Draw user coastline as polylines with antimeridian NaN breaks."""
    ax = plt.gca()

    lkw: dict = {}
    if color_arg is not None:
        lkw['color'] = color_arg
    else:
        lkw.setdefault('color', 'k')
    lkw.setdefault('linewidth', 0.5)
    lkw.update(kwargs)

    x_range = state.x_limits[1] - state.x_limits[0]
    jump_thresh = x_range * 0.5

    for lon, lat in segments:
        x, y = m_ll2xy(lon, lat, clip='off')
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        invalid = ~(np.isfinite(x) & np.isfinite(y))
        x[invalid] = np.nan
        y[invalid] = np.nan
        if jump_thresh > 0 and len(x) > 1:
            dx = np.abs(np.diff(np.where(np.isfinite(x), x, np.nan)))
            jump_idx = np.where(dx > jump_thresh)[0] + 1
            if len(jump_idx):
                x = np.insert(x, jump_idx, np.nan)
                y = np.insert(y, jump_idx, np.nan)
        ax.plot(x, y, **lkw)


def _draw_patch(segments, seg_areas, color_arg, state, **kwargs) -> None:
    """Draw user coastline as filled polygons with map-aware clipping."""
    ax = plt.gca()

    pkw: dict = {}
    if color_arg is not None:
        pkw['facecolor'] = color_arg
    else:
        pkw['facecolor'] = [0.7, 0.7, 0.7]
    pkw.setdefault('edgecolor', 'k')
    pkw.setdefault('linewidth', 0.3)
    for k, v in kwargs.items():
        if k == 'fc':
            pkw['facecolor'] = v
        elif k == 'ec':
            pkw['edgecolor'] = v
        else:
            pkw[k] = v

    proj_type = state.projection_type

    if proj_type == 'circular':
        from shapely.geometry import Point
        R_map = float(state.x_limits[1])
        clip_geom = Point(0.0, 0.0).buffer(R_map * 0.9995, resolution=256)
        _draw_patch_projected_clip(ax, segments, seg_areas, pkw, clip_geom, state)

    elif proj_type == 'oblique':
        from shapely.geometry import box as shapely_box
        x0, x1 = state.x_limits
        y0, y1 = state.y_limits
        clip_geom = shapely_box(x0, y0, x1, y1)
        _draw_patch_projected_clip(ax, segments, seg_areas, pkw, clip_geom, state)

    else:
        # Geographic clip: clip in lon/lat space, then project
        from shapely.geometry import box as shapely_box
        lon_min, lon_max = state.lon_limits
        lat_min, lat_max = state.lat_limits
        geo_rect = shapely_box(lon_min, lat_min, lon_max, lat_max)
        _draw_patch_geo_clip(ax, segments, seg_areas, pkw, geo_rect, state)


def _draw_patch_projected_clip(ax, segments, seg_areas, pkw, clip_geom, state) -> None:
    """
    Project each ring to map coords, clip against clip_geom (in map space),
    then fill.  Used for circular and oblique projections.
    """
    from shapely.geometry import Polygon as SPoly
    from shapely.validation import make_valid

    margin = max(
        state.x_limits[1] - state.x_limits[0],
        state.y_limits[1] - state.y_limits[0],
    ) * 10

    for (lon, lat), _area in zip(segments, seg_areas):
        if len(lon) < 3:
            continue
        lon, lat = _close_ring(lon, lat)
        lon, lat = _densify_ring(lon, lat, max_deg=1.5)

        x, y = m_ll2xy(lon, lat, clip='off')
        x, y = np.asarray(x, float), np.asarray(y, float)
        x = np.where(np.isfinite(x), x, state.x_limits[0] - margin)
        y = np.where(np.isfinite(y), y, state.y_limits[0] - margin)

        try:
            poly = SPoly(zip(x, y))
            if not poly.is_valid:
                poly = make_valid(poly)
            clipped = poly.intersection(clip_geom)
        except Exception:
            continue

        _fill_clipped(ax, clipped, pkw)


def _draw_patch_geo_clip(ax, segments, seg_areas, pkw, geo_rect, state) -> None:
    """
    Clip each ring in geographic (lon/lat) space, then project and fill.
    Used for rectangular, conic, and pseudocylindrical projections.
    """
    from shapely.geometry import Polygon as SPoly
    from shapely.validation import make_valid

    for (lon, lat), _area in zip(segments, seg_areas):
        if len(lon) < 3:
            continue
        lon, lat = _close_ring(lon, lat)
        lon, lat = _densify_ring(lon, lat, max_deg=1.5)

        try:
            geo_poly = SPoly(zip(lon, lat))
            if not geo_poly.is_valid:
                geo_poly = make_valid(geo_poly)
            clipped = geo_poly.intersection(geo_rect)
        except Exception:
            continue

        if clipped.is_empty:
            continue

        parts = (
            list(clipped.geoms)
            if clipped.geom_type in ('MultiPolygon', 'GeometryCollection')
            else [clipped]
        )
        for part in parts:
            if part.geom_type != 'Polygon' or part.is_empty:
                continue
            c = np.asarray(part.exterior.coords, float)
            xp, yp = m_ll2xy(c[:, 0], c[:, 1], clip='off')
            xp, yp = np.asarray(xp, float), np.asarray(yp, float)
            if np.any(np.isfinite(xp)):
                ax.fill(xp, yp, **pkw)


def _draw_speckle(segments, color_arg, state, **kwargs) -> None:
    """Draw speckle (dot markers on the land side of each polygon)."""
    from .hatch import m_hatch

    color = color_arg if color_arg is not None else 'k'
    step = kwargs.pop('step', 5)

    for lon, lat in segments:
        if len(lon) < 3:
            continue
        lon, lat = _close_ring(lon, lat)
        try:
            m_hatch(lon, lat, style='speckle', angle=step, step=step,
                    color=color, **kwargs)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tiny utilities
# ---------------------------------------------------------------------------

def _close_ring(lon: np.ndarray, lat: np.ndarray):
    """Return a closed ring (first == last point)."""
    if lon[0] != lon[-1] or lat[0] != lat[-1]:
        lon = np.append(lon, lon[0])
        lat = np.append(lat, lat[0])
    return lon, lat


def _fill_clipped(ax, clipped, pkw) -> None:
    """Fill all Polygon parts from a Shapely clipping result."""
    if clipped.is_empty:
        return
    result_polys = (
        list(clipped.geoms)
        if clipped.geom_type in ('MultiPolygon', 'GeometryCollection')
        else [clipped]
    )
    for rp in result_polys:
        if rp.geom_type != 'Polygon' or rp.is_empty:
            continue
        cx, cy = rp.exterior.xy
        ax.fill(np.array(cx), np.array(cy), **pkw)
