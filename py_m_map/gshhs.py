"""
GSHHS (Global Self-consistent Hierarchical High-resolution Shorelines)
coastline and landmass drawing.

Functions
---------
m_gshhs       — draw GSHHS coastlines (specify scale)
m_gshhs_c     — crude        resolution (~480 km)
m_gshhs_l     — low          resolution (~108 km)
m_gshhs_i     — intermediate resolution (~23 km)
m_gshhs_h     — high         resolution (~0.2 km)
m_gshhs_f     — full         resolution (~0.04 km)

Hierarchical patch rendering: level 1 (land) and 3 (islands in lakes) are
filled with the requested colour; levels 2 (lakes) and 4 (ponds) are filled
with the axes background colour to cut them out.  Missing levels (e.g. ponds
in crude scale) are silently skipped.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state
from .coast import _densify_ring
from .hatch import _hatch_xy

_LEVELS = (1, 2, 3, 4)

#: Every GSHHS load that failed this session, as (scale, level, reason).
#:
#: A failure only warns and omits the coastline, so a figure can come out looking
#: like a valid map with no coast and nothing to signal it (REVIEW.md M16). Callers
#: that need to know — the image-baseline fixture, which cannot meaningfully compare
#: a figure whose data was unavailable — can read this instead of scraping warnings.
#: Use `load_failures()` and `clear_load_failures()`.
_LOAD_FAILURES: list[tuple[str, int, str]] = []


def load_failures() -> list[tuple[str, int, str]]:
    """GSHHS loads that failed so far, as (scale, level, reason)."""
    return list(_LOAD_FAILURES)


def clear_load_failures() -> None:
    """Forget recorded GSHHS load failures."""
    _LOAD_FAILURES.clear()


def _load_gshhs_geoms(scale: str, level: int) -> list:
    """Return GSHHS geometries for *scale* / *level*, or [] if unavailable."""
    import warnings
    try:
        from cartopy.io.shapereader import gshhs as gshhs_path, Reader
        path = gshhs_path(scale, level)
        return list(Reader(path).geometries())
    except Exception as e:
        _LOAD_FAILURES.append((scale, level, str(e)))
        warnings.warn(
            f"m_gshhs: could not load GSHHS '{scale}' scale level {level} — {e}. "
            "Coastlines will be omitted. Check your internet connection or "
            "pre-download the data with: "
            "python -c \"import cartopy.io.shapereader as s; s.gshhs('c',1)\"",
            UserWarning,
            stacklevel=4,
        )
        return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def m_gshhs(scale: str, style: str = 'patch', *args, **kwargs) -> None:
    """
    Draw GSHHS coastlines on the current map.

    Parameters
    ----------
    scale : {'c', 'l', 'i', 'h', 'f'}
        Resolution: crude, low, intermediate, high, full.
    style : {'patch', 'line'}
        'patch' — hierarchical filled polygons (land + lake/island cutouts).
        'line'  — coastline as lines only.
    *args
        Optional positional colour argument (MATLAB compatibility).
        E.g. ``m_gshhs_l('patch', [.4, .6, .4])`` sets facecolor.
    **kwargs
        Forwarded to ``ax.fill()`` or ``ax.plot()``.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    color_arg = args[0] if args else None

    if style == 'patch':
        _draw_patch(scale, color_arg, state, **kwargs)
    elif style == 'speckle':
        _draw_speckle_coast(scale, color_arg, state, **kwargs)
    else:
        _draw_line(scale, color_arg, state, **kwargs)


def m_gshhs_c(style: str = 'patch', *args, **kwargs) -> None:
    """GSHHS crude resolution (~480 km). See m_gshhs for parameters."""
    m_gshhs('c', style, *args, **kwargs)


def m_gshhs_l(style: str = 'patch', *args, **kwargs) -> None:
    """GSHHS low resolution (~108 km). See m_gshhs for parameters."""
    m_gshhs('l', style, *args, **kwargs)


def m_gshhs_i(style: str = 'patch', *args, **kwargs) -> None:
    """GSHHS intermediate resolution (~23 km). See m_gshhs for parameters."""
    m_gshhs('i', style, *args, **kwargs)


def m_gshhs_h(style: str = 'patch', *args, **kwargs) -> None:
    """GSHHS high resolution (~0.2 km). See m_gshhs for parameters."""
    m_gshhs('h', style, *args, **kwargs)


def m_gshhs_f(style: str = 'patch', *args, **kwargs) -> None:
    """GSHHS full resolution (~0.04 km). See m_gshhs for parameters."""
    m_gshhs('f', style, *args, **kwargs)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _draw_patch(scale: str, color_arg, state, **kwargs) -> None:
    ax = plt.gca()

    pkw_land: dict = {}
    if color_arg is not None:
        pkw_land['facecolor'] = color_arg
    else:
        pkw_land['facecolor'] = [0.7, 0.7, 0.7]
    pkw_land.setdefault('edgecolor', 'none')
    pkw_land.setdefault('linewidth', 0.3)
    for k, v in kwargs.items():
        if k == 'fc':
            pkw_land['facecolor'] = v
        elif k == 'ec':
            pkw_land['edgecolor'] = v
        else:
            pkw_land[k] = v

    bg_color = ax.get_facecolor()
    pkw_water = dict(pkw_land)
    pkw_water['facecolor'] = bg_color
    pkw_water['edgecolor'] = 'none'

    level_pkw = {1: pkw_land, 2: pkw_water, 3: pkw_land, 4: pkw_water}

    for level in _LEVELS:
        geoms = _load_gshhs_geoms(scale, level)
        if not geoms:
            continue
        pkw = dict(level_pkw[level])
        pkw['zorder'] = level

        if state.projection_name == 'orthographic':
            R_map = float(state.x_limits[1])
            _draw_geoms_circular(ax, geoms, pkw, state, R_map)
        elif state.projection_type == 'oblique':
            _draw_geoms_oblique(ax, geoms, pkw, state)
        else:
            _draw_geoms_geographic_clip(ax, geoms, pkw, state)


def _draw_geoms_geographic_clip(ax, geoms, pkw, state) -> None:
    """Project and clip polygon geometries to the geographic bounding box."""
    from shapely.geometry import box as shapely_box
    from shapely.validation import make_valid
    from matplotlib.collections import PolyCollection

    lon_min, lon_max = state.lon_limits
    lat_min, lat_max = state.lat_limits

    antimeridian = lon_max > 180.0
    if antimeridian:
        lon_max_geo = lon_max - 360.0
        box1 = shapely_box(lon_min, lat_min, 180.0, lat_max)
        box2 = shapely_box(-180.0, lat_min, lon_max_geo, lat_max)
        geo_rect = box1.union(box2)
    else:
        geo_rect = shapely_box(lon_min, lat_min, lon_max, lat_max)

    xy_polys = []
    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            pb = poly.bounds
            if pb[3] < lat_min or pb[1] > lat_max:
                continue
            if antimeridian:
                in_east = pb[2] >= lon_min and pb[0] <= 180.0
                in_west = pb[2] >= -180.0 and pb[0] <= lon_max_geo
                if not (in_east or in_west):
                    continue
            else:
                if pb[2] < lon_min or pb[0] > lon_max:
                    continue
            try:
                if not poly.is_valid:
                    poly = make_valid(poly)
                clipped = poly.intersection(geo_rect)
            except Exception:
                continue
            if clipped.is_empty:
                continue

            result_polys = (
                list(clipped.geoms)
                if clipped.geom_type in ('MultiPolygon', 'GeometryCollection')
                else [clipped]
            )
            for rp in result_polys:
                if rp.geom_type != 'Polygon' or rp.is_empty:
                    continue
                coords = np.asarray(rp.exterior.coords, dtype=float)
                lon, lat = coords[:, 0], coords[:, 1]
                if antimeridian:
                    lon = np.where(lon < lon_min, lon + 360.0, lon)
                lon, lat = _densify_ring(lon, lat, max_deg=1.5)
                x, y = m_ll2xy(lon, lat, clip='off')
                x, y = np.asarray(x, float), np.asarray(y, float)
                if np.any(np.isfinite(x)):
                    xy_polys.append(np.column_stack([x, y]))

    if xy_polys:
        ax.add_collection(PolyCollection(xy_polys, **pkw))


def _draw_geoms_oblique(ax, geoms, pkw, state) -> None:
    """Project and clip polygon geometries for oblique Mercator projections."""
    from shapely.geometry import Polygon as SPoly, box as shapely_box
    from shapely.validation import make_valid

    x0, x1 = state.x_limits
    y0, y1 = state.y_limits
    map_rect = shapely_box(x0, y0, x1, y1)

    if state.coast_lon_limits is not None:
        lon_min, lon_max = state.coast_lon_limits
        lat_min, lat_max = state.coast_lat_limits
    else:
        lon_min, lon_max = state.lon_limits
        lat_min, lat_max = state.lat_limits
    margin = max(x1 - x0, y1 - y0) * 10

    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            pb = poly.bounds
            if pb[3] < lat_min or pb[1] > lat_max:
                continue
            if pb[2] < lon_min or pb[0] > lon_max:
                continue

            coords = np.asarray(list(poly.exterior.coords), dtype=float)
            lon, lat = coords[:, 0], coords[:, 1]
            lon, lat = _densify_ring(lon, lat, max_deg=1.5)
            x, y = m_ll2xy(lon, lat, clip='off')
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)
            x = np.where(np.isfinite(x), x, x0 - margin)
            y = np.where(np.isfinite(y), y, y0 - margin)

            try:
                proj_poly = SPoly(zip(x, y))
                if not proj_poly.is_valid:
                    proj_poly = make_valid(proj_poly)
                clipped = proj_poly.intersection(map_rect)
            except Exception:
                continue
            if clipped.is_empty:
                continue

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


def _draw_geoms_circular(ax, geoms, pkw, state, R_map: float) -> None:
    """Project and clip polygon geometries for circular projections (ortho/stereo)."""
    from shapely.geometry import Polygon as SPoly, Point
    from shapely.validation import make_valid

    R = R_map
    safe = 3.0 * R
    horizon_disk = Point(0.0, 0.0).buffer(R * 0.9995, resolution=256)

    is_ortho = (state.projection_name == 'orthographic')
    if is_ortho:
        lat0_r = np.radians(state.center_lat)
        lon0_r = np.radians(state.center_lon)

    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            coords = np.asarray(list(poly.exterior.coords), dtype=float)
            lon, lat = coords[:, 0], coords[:, 1]
            lon, lat = _densify_ring(lon, lat, max_deg=1.5)
            x, y = m_ll2xy(lon, lat, clip='off')
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)

            back = ~(np.isfinite(x) & np.isfinite(y))
            if np.any(back):
                if is_ortho:
                    lat_r = np.radians(lat[back])
                    lon_r = np.radians(lon[back])
                    xb = np.cos(lat_r) * np.sin(lon_r - lon0_r)
                    yb = (np.sin(lat_r) * np.cos(lat0_r)
                          - np.cos(lat_r) * np.sin(lat0_r) * np.cos(lon_r - lon0_r))
                    rb = np.hypot(xb, yb)
                    rb = np.where(rb < 1e-10, 1.0, rb)
                    x = x.copy()
                    y = y.copy()
                    x[back] = safe * xb / rb
                    y[back] = safe * yb / rb
                else:
                    x = np.where(np.isfinite(x), x, safe)
                    y = np.where(np.isfinite(y), y, safe)

            try:
                proj_poly = SPoly(zip(x, y))
                if not proj_poly.is_valid:
                    proj_poly = make_valid(proj_poly)
                clipped = proj_poly.intersection(horizon_disk)
            except Exception:
                continue
            if clipped.is_empty:
                continue

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


def _draw_speckle_coast(scale: str, color_arg, state, **kwargs) -> None:
    """Scatter speckle dots along coastline polygons (land side)."""
    ax = plt.gca()

    kw: dict = {}
    if color_arg is not None:
        kw['color'] = color_arg
    kw.update(kwargs)

    lon_min, lon_max = state.lon_limits
    lat_min, lat_max = state.lat_limits

    geoms = _load_gshhs_geoms(scale, 1)
    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            pb = poly.bounds
            if pb[3] < lat_min or pb[1] > lat_max:
                continue
            if pb[2] < lon_min or pb[0] > lon_max:
                continue
            coords = np.asarray(list(poly.exterior.coords), dtype=float)
            lon, lat = coords[:, 0], coords[:, 1]
            lon, lat = _densify_ring(lon, lat, max_deg=1.5)
            x, y = m_ll2xy(lon, lat, clip='off')
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)
            _hatch_xy(ax, x, y, 'speckle', angle=5, step=2, **kw)


def _draw_line(scale: str, color_arg, state, **kwargs) -> None:
    """Draw GSHHS L1 coastline as lines."""
    ax = plt.gca()

    lkw: dict = {}
    if color_arg is not None:
        lkw['color'] = color_arg
    else:
        lkw['color'] = 'k'
    lkw.setdefault('linewidth', 0.5)
    lkw.update(kwargs)

    geoms = _load_gshhs_geoms(scale, 1)
    x_range = state.x_limits[1] - state.x_limits[0]
    jump_thresh = x_range * 0.5

    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            coords = np.asarray(list(poly.exterior.coords), dtype=float)
            if len(coords) < 2:
                continue
            lon, lat = coords[:, 0], coords[:, 1]
            x, y = m_ll2xy(lon, lat, clip='off')
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)
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
