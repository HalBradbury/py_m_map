"""
Coastline drawing using Natural Earth data via cartopy.

m_coast — ported from m_coast.m / mu_coast.m
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state

_R_EARTH = 6370997.0  # sphere radius (m_map default)


def _auto_resolution(state) -> str:
    """Select Natural Earth resolution based on map extent."""
    lon_span = abs(state.lon_limits[1] - state.lon_limits[0])
    lat_span = abs(state.lat_limits[1] - state.lat_limits[0])
    span = max(lon_span, lat_span)
    if span < 30:
        return '10m'
    elif span < 90:
        return '50m'
    return '110m'


def m_coast(style: str = 'line', *args, resolution: str | None = None, **kwargs) -> None:
    """
    Draw coastlines on the current map.

    Parameters
    ----------
    style : {'line', 'patch'}
        'line'  — draw coastline as lines (fast, default).
        'patch' — draw land as filled polygons.
    resolution : {'10m', '50m', '110m'} or None
        Natural Earth coastline resolution.  None (default) auto-selects
        based on map extent: '10m' for regional (<30° span), '50m' for
        continental (<90°), '110m' for global.
    *args
        Optional positional colour argument (MATLAB compatibility).
        E.g. ``m_coast('patch', 'r')`` sets facecolor='r'.
    **kwargs
        Forwarded to ``ax.plot()`` (line) or ``ax.fill()`` (patch).
        Common keys: ``color``, ``facecolor``, ``edgecolor``, ``linewidth``.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    if resolution is None:
        resolution = _auto_resolution(state)

    color_arg = args[0] if args else None

    if style == 'patch':
        _draw_patch(color_arg, state, resolution=resolution, **kwargs)
    else:
        _draw_line(color_arg, state, resolution=resolution, **kwargs)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_geoms(kind: str, resolution: str = '110m'):
    from cartopy.io.shapereader import natural_earth, Reader
    shpfile = natural_earth(resolution=resolution, category='physical', name=kind)
    return list(Reader(shpfile).geometries())


def _draw_patch(color_arg, state, resolution: str = '110m', **kwargs) -> None:
    """Draw land as filled polygons."""
    ax = plt.gca()

    pkw: dict = {}
    if color_arg is not None:
        pkw['facecolor'] = color_arg
    else:
        pkw['facecolor'] = [0.7, 0.7, 0.7]
    pkw.setdefault('edgecolor', 'k')
    pkw.setdefault('linewidth', 0.3)
    # Merge caller kwargs, normalising short-form aliases (fc/ec → facecolor/edgecolor)
    for k, v in kwargs.items():
        if k == 'fc':
            pkw['facecolor'] = v
        elif k == 'ec':
            pkw['edgecolor'] = v
        else:
            pkw[k] = v
    if state.projection_type == 'circular':
        # Circular projections (orthographic, stereographic, LAEA, …): clip in
        # projected space to the map disk via shapely intersection.
        R_map = float(state.x_limits[1])
        _draw_patch_circular(ax, pkw, R_map, resolution=resolution)
    elif state.projection_type == 'oblique':
        # Oblique Mercator: clip in projected (x, y) space to the map rectangle.
        # The geographic bounding box is set wide in m_proj; shapely intersection
        # with the x_limits × y_limits rectangle does the final clipping.
        _draw_patch_oblique_clip(ax, pkw, state, resolution=resolution)
    else:
        # All other projections (conic, equidistant, stereographic cap …):
        # clip to the geographic lat/lon bounding box before projecting.
        # For polar stereographic the geographic box (lon: −180–180,
        # lat: lat_c−r … lat_c+r) maps exactly to the cap circle, so no
        # land can spill outside the boundary.
        _draw_patch_geographic_clip(ax, pkw, state, resolution=resolution)


def _draw_patch_oblique_clip(ax, pkw, state, resolution: str = '110m') -> None:
    """
    Fill land polygons clipped to the oblique Mercator map rectangle.

    Projects all candidate land polygons (pre-filtered by the wide geographic
    bounding box stored in state.coast_lon/lat_limits) into the oblique (x, y)
    space, then intersects each projected polygon with the x_limits × y_limits
    rectangle using shapely.  This is the correct approach because the oblique
    map boundary is a rectangle in projected space, not in geographic space.
    """
    from shapely.geometry import Polygon as SPoly, box as shapely_box
    from shapely.validation import make_valid

    x0, x1 = state.x_limits
    y0, y1 = state.y_limits
    map_rect = shapely_box(x0, y0, x1, y1)

    # Use wide coast limits when available (stored separately from tick limits)
    if state.coast_lon_limits is not None:
        lon_min, lon_max = state.coast_lon_limits
        lat_min, lat_max = state.coast_lat_limits
    else:
        lon_min, lon_max = state.lon_limits
        lat_min, lat_max = state.lat_limits
    margin = max(x1 - x0, y1 - y0) * 10  # proxy for out-of-range vertices

    geoms = _load_geoms('land', resolution=resolution)

    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            # Quick geographic AABB rejection
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

            # Replace non-finite values with an out-of-range proxy so shapely
            # can build a valid polygon; the intersection removes them.
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


def _split_ring_at_cut(lon: np.ndarray, lat: np.ndarray, cut_lon: float):
    """
    Split a closed polygon ring at the cut_lon meridian.

    Returns a list of (lon_arr, lat_arr) closed sub-rings in geographic
    [-180, 180] coordinates.  If the ring does not cross cut_lon the
    original arrays are returned unchanged (as a single-element list).

    lon/lat must be a closed ring: last point == first point.

    Boundary vertices are offset by ±_EPS degrees from the exact cut so
    that each sub-ring's edge vertex projects to the correct map edge
    (Hammer / pseudocylindrical projections evaluate lon=cut_lon to
    only one of the two edges; the small offset disambiguates them).
    """
    lon_u = lon[:-1]
    lat_u = lat[:-1]
    n = len(lon_u)
    if n < 3:
        return [(lon, lat)]

    # Normalise to [0, 360) relative to cut_lon.
    # lon_n ∈ (0, 180)  → geographically between cut and center  → LEFT  half (x < 0)
    # lon_n ∈ (180, 360) → geographically between center and cut  → RIGHT half (x > 0)
    lon_n = (lon_u - cut_lon) % 360.0

    # Circular diff (including the wrap-around edge n-1 → 0)
    diffs = np.empty(n)
    diffs[:-1] = np.diff(lon_n)
    diffs[-1] = lon_n[0] - lon_n[-1]

    if not np.any(np.abs(diffs) > 180):
        return [(lon, lat)]

    # Small offset so each boundary vertex projects to a unique edge pixel.
    _EPS = 0.01   # degrees; ~1 km, invisible in any projection

    sub_rings_raw: list[tuple[list, list]] = []
    cur_lon: list[float] = []
    cur_lat: list[float] = []

    for i in range(n):
        cur_lon.append(float(lon_n[i]))
        cur_lat.append(float(lat_u[i]))

        if abs(diffs[i]) > 180:
            next_i = (i + 1) % n
            d_raw = diffs[i]
            if d_raw < -180.0:
                # RIGHT half (lon_n near 360) → LEFT half (lon_n near 0)
                # Interpolate at the 360 boundary; close RIGHT sub-ring just
                # inside 360, start LEFT sub-ring just above 0.
                d_unwrap = d_raw + 360.0
                cut_exact = 360.0
                cut_at = 360.0 - _EPS   # just inside RIGHT half
                restart_at = _EPS        # just inside LEFT half
            else:
                # LEFT half (lon_n near 0) → RIGHT half (lon_n near 360)
                d_unwrap = d_raw - 360.0
                cut_exact = 0.0
                cut_at = _EPS            # just inside LEFT half
                restart_at = 360.0 - _EPS  # just inside RIGHT half

            t = (cut_exact - lon_n[i]) / d_unwrap if abs(d_unwrap) > 1e-10 else 0.0
            lat_cut = float(lat_u[i] + t * (lat_u[next_i] - lat_u[i]))

            cur_lon.append(cut_at)
            cur_lat.append(lat_cut)
            sub_rings_raw.append((list(cur_lon), list(cur_lat)))
            cur_lon = [restart_at]
            cur_lat = [lat_cut]

    # Remaining points belong to the first sub-ring (ring is closed)
    if sub_rings_raw:
        merged_lon = cur_lon + sub_rings_raw[0][0]
        merged_lat = cur_lat + sub_rings_raw[0][1]
        sub_rings_raw[0] = (merged_lon, merged_lat)
    else:
        sub_rings_raw.append((cur_lon, cur_lat))

    result = []
    for sl, slat in sub_rings_raw:
        if len(sl) < 3:
            continue
        sl_arr = ((np.array(sl) + cut_lon + 180.0) % 360.0) - 180.0
        slat_arr = np.array(slat)
        # Close the ring
        sl_arr = np.append(sl_arr, sl_arr[0])
        slat_arr = np.append(slat_arr, slat_arr[0])
        result.append((sl_arr, slat_arr))

    return result if result else [(lon, lat)]


def _draw_patch_geographic_clip(ax, pkw, state, resolution: str = '110m') -> None:
    """
    Fill land polygons clipped to the current geographic lat/lon extent.

    For full-world pseudocylindrical projections (Hammer, Mollweide, etc.)
    each polygon ring is split at the projection's cut meridian before
    projecting, so no ring straddles the discontinuity and produces a
    cross-map fill band.  All other projections use shapely intersection
    with the geographic bounding box.
    """
    from shapely.geometry import box as shapely_box
    from shapely.validation import make_valid

    lon_min, lon_max = state.lon_limits
    lat_min, lat_max = state.lat_limits

    is_pseudo_full = (
        getattr(state, 'projection_type', '') == 'pseudocylindrical'
        and (lon_max - lon_min) >= 359.9
    )

    geoms = _load_geoms('land', resolution=resolution)

    if is_pseudo_full:
        clon = getattr(state, 'center_lon', 0.0)
        cut = clon % 360.0 - 180.0  # cut meridian in [-180, 180)

        # Clip each polygon to the two half-worlds on either side of the cut.
        # This avoids the self-intersecting closing edge produced by
        # _split_ring_at_cut when a circumpolar polygon crosses the cut only once.
        _CUT_EPS = 0.01  # degrees; nudges boundary vertices to the correct map edge

        west_box = shapely_box(-181.0, -91.0, cut, 91.0)
        east_box = shapely_box(cut, -91.0, 181.0, 91.0)

        for geom in geoms:
            polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
            for poly in polys:
                pb = poly.bounds
                if pb[3] < lat_min or pb[1] > lat_max:
                    continue
                if not poly.is_valid:
                    try:
                        poly = make_valid(poly)
                    except Exception:
                        continue

                for box_geom, cut_nudge in ((west_box, -_CUT_EPS), (east_box, +_CUT_EPS)):
                    try:
                        part = poly.intersection(box_geom)
                    except Exception:
                        continue
                    if part.is_empty:
                        continue
                    part_list = (
                        list(part.geoms)
                        if part.geom_type in ('MultiPolygon', 'GeometryCollection')
                        else [part]
                    )
                    for rp in part_list:
                        if rp.geom_type != 'Polygon' or rp.is_empty:
                            continue
                        rp_coords = np.asarray(rp.exterior.coords, dtype=float)
                        rp_lon, rp_lat = rp_coords[:, 0], rp_coords[:, 1]
                        # Boundary vertices placed at lon=cut by shapely are
                        # ambiguous: pyproj maps them to x_max (offset=+180°)
                        # regardless of which half-world sub-polygon they belong
                        # to.  Nudging them by ±eps forces each to the correct
                        # map edge before projection and eliminates full-width
                        # fill bands from polygons that straddle the cut.
                        at_cut = np.abs(rp_lon - cut) < 0.005
                        if np.any(at_cut):
                            rp_lon = rp_lon.copy()
                            rp_lon[at_cut] += cut_nudge
                        rp_lon, rp_lat = _densify_ring(rp_lon, rp_lat, max_deg=1.5, wrap=False)
                        x, y = m_ll2xy(rp_lon, rp_lat, clip='off')
                        x, y = np.asarray(x, float), np.asarray(y, float)
                        if np.any(np.isfinite(x)):
                            ax.fill(x, y, **pkw)
        return

    # --- Non-pseudo-full: clip to geographic bounding box via shapely ---
    antimeridian = lon_max > 180.0
    if antimeridian:
        lon_max_geo = lon_max - 360.0
        b1 = shapely_box(lon_min, lat_min, 180.0, lat_max)
        b2 = shapely_box(-180.0, lat_min, lon_max_geo, lat_max)
        geo_rect = b1.union(b2)
    else:
        geo_rect = shapely_box(lon_min, lat_min, lon_max, lat_max)

    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            pb = poly.bounds
            if pb[3] < lat_min or pb[1] > lat_max:
                continue
            if antimeridian:
                lon_max_geo = lon_max - 360.0
                in_east = pb[2] >= lon_min and pb[0] <= 180.0
                in_west = pb[2] >= -180.0 and pb[0] <= lon_max_geo
                if not (in_east or in_west):
                    continue
            else:
                if pb[2] < lon_min or pb[0] > lon_max:
                    continue

            if not poly.is_valid:
                try:
                    poly = make_valid(poly)
                except Exception:
                    continue

            try:
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
                    ax.fill(x, y, **pkw)


def _densify_ring(lon: np.ndarray, lat: np.ndarray, max_deg: float = 1.5, wrap: bool = True):
    """
    Insert intermediate points along polygon edges so that no edge spans
    more than `max_deg` degrees.  This eliminates straight-chord artefacts
    where a horizon-crossing edge is replaced by a single proxy point.

    wrap=True (default): adjust dlon by ±360 when |dlon|>180 (antimeridian
    wrapping for standard [-180,180] rings).  wrap=False: trace the literal
    longitude path, needed for shapely-clipped sub-polygons whose coordinates
    are already in a consistent half-world range (e.g. [-180, 30]).
    """
    new_lon = [lon[0]]
    new_lat = [lat[0]]
    for i in range(1, len(lon)):
        dlon = lon[i] - lon[i - 1]
        # Handle antimeridian wrapping
        if wrap and abs(dlon) > 180:
            dlon -= np.sign(dlon) * 360
        dlat = lat[i] - lat[i - 1]
        # Approximate great-circle step in degrees
        cos_lat = np.cos(np.radians((lat[i] + lat[i - 1]) / 2.0))
        dist = max(abs(dlon) * cos_lat, abs(dlat))
        n = max(1, int(np.ceil(dist / max_deg)))
        for j in range(1, n + 1):
            frac = j / n
            new_lon.append(lon[i - 1] + frac * dlon)
            new_lat.append(lat[i - 1] + frac * dlat)
    return np.array(new_lon), np.array(new_lat)


def _draw_patch_circular(ax, pkw, R_map: float = _R_EARTH, resolution: str = '110m') -> None:
    """
    Fill land polygons for circular projections (ortho, stereo cap, etc.).

    Parameters
    ----------
    R_map : float
        Radius of the map disk in projection metres.  For orthographic this is
        R_EARTH; for a stereographic cap it is 2·R·tan(r/2).

    Each land polygon is:
      1. Densified (intermediate vertices inserted every ≤1.5° along each edge)
         so that horizon-crossing edges produce only tiny straight artefacts.
      2. Clipped to the visible map disk via shapely intersection,
         guaranteeing correct polygon topology — no triangle fragments.
    """
    from shapely.geometry import Polygon as SPoly, Point
    from shapely.validation import make_valid

    state = get_state()
    R = R_map
    safe = 3.0 * R
    # Visible map disk (slightly smaller to avoid fringe artefacts)
    _origin = Point(0.0, 0.0)
    horizon_disk = _origin.buffer(R * 0.9995, resolution=256)

    # Pre-compute orthographic projection centre in radians (for directional proxy).
    is_ortho = (state.projection_name == 'orthographic')
    if is_ortho:
        lat0_r = np.radians(state.center_lat)
        lon0_r = np.radians(state.center_lon)

    geoms = _load_geoms('land', resolution=resolution)

    for geom in geoms:
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        for poly in polys:
            coords = np.asarray(list(poly.exterior.coords), dtype=float)
            lon, lat = coords[:, 0], coords[:, 1]

            # Densify so horizon-crossings happen within ≤1.5° of a vertex
            lon, lat = _densify_ring(lon, lat, max_deg=1.5)

            x, y = m_ll2xy(lon, lat, clip='off')
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)

            # Replace back-hemisphere (non-finite) points with a directional
            # proxy outside the disk.  For orthographic projections, use the
            # analytic formula to get the correct direction for each point
            # instead of collapsing them all to a single corner — that collapse
            # creates spurious chords when the shapely intersection clips the
            # triangle back to the disk boundary.
            back = ~(np.isfinite(x) & np.isfinite(y))
            if np.any(back):
                if is_ortho:
                    lat_r = np.radians(lat[back])
                    lon_r = np.radians(lon[back])
                    xb = np.cos(lat_r) * np.sin(lon_r - lon0_r)
                    yb = (np.sin(lat_r) * np.cos(lat0_r)
                          - np.cos(lat_r) * np.sin(lat0_r) * np.cos(lon_r - lon0_r))
                    rb = np.hypot(xb, yb)
                    # Avoid division by zero at the exact antipodal point
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
                # For projections like LAEA that map the entire sphere, very
                # large land polygons (e.g. Africa+Eurasia) can project such
                # that their 2-D interior encloses the map centre (ocean) rather
                # than the land. Detect this by comparing whether the geographic
                # polygon contains the projection centre with whether the
                # projected intersection contains the origin.
                if not clipped.is_empty:
                    geo_ctr_land = poly.contains(
                        Point(state.center_lon, state.center_lat)
                    ) if (state.center_lon is not None
                          and state.center_lat is not None) else False
                    proj_ctr_in = clipped.contains(_origin)
                    if geo_ctr_land != proj_ctr_in:
                        clipped = horizon_disk.difference(proj_poly)
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


def _draw_line(color_arg, state, resolution: str = '110m', **kwargs) -> None:
    """Draw coastlines as lines."""
    ax = plt.gca()

    lkw: dict = {}
    if color_arg is not None:
        lkw['color'] = color_arg
    else:
        lkw['color'] = 'k'
    lkw.setdefault('linewidth', 0.5)
    lkw.update(kwargs)

    geoms = _load_geoms('coastline', resolution=resolution)

    # Threshold for detecting antimeridian / wrap-around jumps in x.
    x_range = state.x_limits[1] - state.x_limits[0]
    jump_thresh = x_range * 0.5

    for geom in geoms:
        lines = list(geom.geoms) if geom.geom_type.startswith('Multi') else [geom]
        for line in lines:
            coords = np.asarray(list(line.coords), dtype=float)
            if len(coords) < 2:
                continue
            lon, lat = coords[:, 0], coords[:, 1]
            x, y = m_ll2xy(lon, lat, clip='off')
            x = np.asarray(x, dtype=float)
            y = np.asarray(y, dtype=float)
            invalid = ~(np.isfinite(x) & np.isfinite(y))
            x[invalid] = np.nan
            y[invalid] = np.nan
            # Break the line where consecutive points jump across the
            # antimeridian (or any large projected discontinuity).
            if jump_thresh > 0 and len(x) > 1:
                dx = np.abs(np.diff(np.where(np.isfinite(x), x, np.nan)))
                jump_idx = np.where(dx > jump_thresh)[0] + 1
                if len(jump_idx):
                    x = np.insert(x, jump_idx, np.nan)
                    y = np.insert(y, jump_idx, np.nan)
            ax.plot(x, y, **lkw)


def m_landmask(lon_grid, lat_grid, resolution: str = '110m') -> np.ndarray:
    """
    Return a boolean array (True = land) for grid points in the current projection.

    Containment is tested in geographic (lon, lat) space using
    matplotlib.path.Path.contains_points, which avoids NaN artefacts from
    projecting shapely polygon vertices and winding-order ambiguities.

    For Pacific-centred projections the cut meridian is detected automatically
    from the projection's lon limits: when lon_max is in (-180, 180) the
    Natural Earth polygons are split there and the eastern half is remapped by
    −360° so the coordinate range is continuous with the grid.

    Parameters
    ----------
    lon_grid, lat_grid : array-like, same shape
        Grid coordinates in the same system as the current projection
        (e.g. [-330, 30] for a Pacific-centred Robinson).
    resolution : {'110m', '50m', '10m'}
        Natural Earth land polygon resolution.
    """
    from cartopy.io.shapereader import natural_earth, Reader
    from shapely.geometry import box as sbox
    from shapely.validation import make_valid
    from matplotlib.path import Path as MPath

    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon_grid = np.asarray(lon_grid, dtype=float)
    lat_grid = np.asarray(lat_grid, dtype=float)
    orig_shape = lon_grid.shape

    lat_min, lat_max = state.lat_limits
    lon_min, lon_max = state.lon_limits

    # Auto-detect cut meridian: when lon_max is away from ±180°, it is the
    # cut where polygons need splitting and eastern half remapping by −360°.
    full_world = (lon_max - lon_min) >= 359.9
    cut = float(lon_max) if (full_world and abs(lon_max) < 179.9) else None

    pts = np.column_stack([lon_grid.ravel(), lat_grid.ravel()])
    land_mask_flat = np.zeros(pts.shape[0], dtype=bool)

    shpfile = natural_earth(resolution=resolution, category='physical', name='land')

    def _ring_contains(ring, lon_shift=0.0):
        """Boolean mask of `pts` inside a single ring, or None if degenerate."""
        verts = [(c[0] + lon_shift, c[1]) for c in ring.coords]
        if len(verts) < 3:
            return None
        codes = ([MPath.MOVETO] + [MPath.LINETO] * (len(verts) - 2)
                 + [MPath.CLOSEPOLY])
        return MPath(verts, codes).contains_points(pts)

    def _add_parts(geom, lon_shift=0.0):
        parts = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
        for poly in parts:
            if poly.geom_type != 'Polygon' or poly.is_empty:
                continue
            inside = _ring_contains(poly.exterior, lon_shift)
            if inside is None or not inside.any():
                continue
            # Interior rings are holes — lakes and inland seas such as the
            # Caspian.  Testing the exterior alone would report their water as
            # land.  Subtract explicitly rather than relying on a compound-path
            # fill rule, which depends on ring winding order that the source
            # shapefile does not guarantee.
            for ring in poly.interiors:
                hole = _ring_contains(ring, lon_shift)
                if hole is not None:
                    inside &= ~hole
            land_mask_flat.__ior__(inside)

    if cut is None:
        full_box = sbox(-180.0, lat_min - 1, 180.0, lat_max + 1)
        for geom in Reader(shpfile).geometries():
            geom = make_valid(geom)
            parts = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
            for poly in parts:
                wp = poly.intersection(full_box)
                if not wp.is_empty:
                    _add_parts(wp)
    else:
        west_box = sbox(-180.0, lat_min - 1, cut,   lat_max + 1)
        east_box = sbox(cut,    lat_min - 1, 180.0,  lat_max + 1)
        for geom in Reader(shpfile).geometries():
            geom = make_valid(geom)
            parts = [geom] if geom.geom_type == 'Polygon' else list(geom.geoms)
            for poly in parts:
                wp = poly.intersection(west_box)
                if not wp.is_empty:
                    _add_parts(wp)
                ep = poly.intersection(east_box)
                if not ep.is_empty:
                    _add_parts(ep, lon_shift=-360.0)

    return land_mask_flat.reshape(orig_shape)


def _project_ring(coords):
    arr = np.asarray(list(coords), dtype=float)
    if len(arr) == 0:
        return np.array([]), np.array([])
    lon, lat = arr[:, 0], arr[:, 1]
    x, y = m_ll2xy(lon, lat, clip='off')
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    invalid = ~(np.isfinite(x) & np.isfinite(y))
    x[invalid] = np.nan
    y[invalid] = np.nan
    return x, y


def _split_valid_segments(x: np.ndarray, y: np.ndarray, min_pts: int = 2):
    nan_mask = np.isnan(x) | np.isnan(y)
    segments = []
    start = None
    for i, is_nan in enumerate(nan_mask):
        if not is_nan and start is None:
            start = i
        elif is_nan and start is not None:
            if i - start >= min_pts:
                segments.append((x[start:i], y[start:i]))
            start = None
    if start is not None and len(x) - start >= min_pts:
        segments.append((x[start:], y[start:]))
    return segments
