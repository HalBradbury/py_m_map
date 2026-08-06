"""
Map projection setup and coordinate transforms.

m_proj  — initialise a projection
m_ll2xy — geographic (lon, lat) → map (x, y)
m_xy2ll — map (x, y) → geographic (lon, lat)
"""
from __future__ import annotations
import numpy as np
import pyproj
from ._state import get_state

_R_EARTH = 6370997.0  # sphere radius in metres (m_map default)

# Prefix-matched aliases (first 3 chars, lower-case)
_PROJ_ALIASES: dict[str, str] = {
    'equ': 'equidistant',
    'eqc': 'equidistant',
    'mer': 'mercator',
    'lam': 'lambert',
    'alb': 'albers',
    'aea': 'albers',
    'ste': 'stereographic',
    'utm': 'utm',
    'mol': 'mollweide',
    'ham': 'hammer',
    'mil': 'miller',
    'rob': 'robinson',
    'ort': 'orthographic',
    'gno': 'gnomeric',
    'azi': 'azimuthal_equidistant',
    'sin': 'sinusoidal',
    'obl': 'oblique',
}


def _reset_projection_fields(state) -> None:
    """
    Clear every projection-derived field on the shared map state.

    Called at the top of m_proj.  Each projection branch sets only the fields it
    needs, so without this a field set by one projection survives into the next
    one — see the x_offset / center_lat leaks this guards against.  Fields that
    are user settings rather than projection outputs (e.g. ellipsoid) are left
    untouched.
    """
    state.x_offset = 0.0
    state.center_lat = 0.0
    state.center_lon = 0.0
    state.coast_lon_limits = None
    state.coast_lat_limits = None
    state.utm_zone = None
    state.utm_south = False
    state.title_y = None


def _conic_standard_parallels(lat_mid: float, lat_span: float) -> tuple[float, float]:
    """
    Standard parallels for the conic projections (lambert, albers).

    MATLAB mp_conic.m uses mean ± span/6, i.e. the 25 % and 75 % points of the
    latitude range.  Proj additionally requires |lat_1 + lat_2| > 0, which that
    formula violates for any range symmetric about the equator (lat_mid == 0).
    In that case both parallels are shifted north by a token amount: it keeps the
    sum non-zero at a cost in distortion far below the width of a plotted line.
    """
    lat_1 = lat_mid - lat_span / 6.0
    lat_2 = lat_mid + lat_span / 6.0
    if abs(lat_1 + lat_2) < 1e-6:
        nudge = max(abs(lat_span) / 60.0, 1e-3)
        lat_1 += nudge
        lat_2 += nudge
    return lat_1, lat_2


class _ObliqueProj:
    """
    Callable wrapper giving the analytic oblique-Mercator transforms the same
    call signature as ``pyproj.Proj``.

    m_ll2xy / m_xy2ll invoke ``state.proj(a, b, inverse=...)``, so storing a bare
    forward closure in ``state.proj`` makes m_xy2ll unusable for this projection.
    """

    __slots__ = ('_fwd', '_inv')

    def __init__(self, fwd, inv):
        self._fwd = fwd
        self._inv = inv

    def __call__(self, a, b, inverse: bool = False):
        return self._inv(a, b) if inverse else self._fwd(a, b)


def m_proj(projection: str, *, lon=None, lat, radius=None, aspect=None, direction='vertical') -> None:
    """
    Initialise a map projection.

    Parameters
    ----------
    projection : str
        Projection name (case-insensitive, prefix-matched). Supported:
        'equidistant' — equidistant cylindrical / plate carrée (regional maps).
        'orthographic' — orthographic globe view (lon/lat are the centre point).
    lon : float or sequence of two floats
        For regional projections: [lon_min, lon_max].
        For global/circular projections (ortho, stereo etc.): single centre longitude.
    lat : float or sequence of two floats
        For regional projections: [lat_min, lat_max].
        For global/circular projections: single centre latitude.
    radius : float, optional
        For 'stereographic': angular radius of the map cap in decimal degrees.
    """
    state = get_state()

    # Every m_proj call defines a fresh projection, but only some branches below
    # set each projection-specific field.  Clear them all first so nothing leaks
    # in from the previous call — x_offset in particular is added to *every*
    # transform in m_ll2xy, so a stale value silently displaces the whole map.
    _reset_projection_fields(state)

    full_lower = projection.lower()
    if 'azimuthal' in full_lower and (
        'equal-area' in full_lower or 'equal area' in full_lower
        or 'equal_area' in full_lower
    ):
        name = 'azimuthal_equal_area'
    else:
        key = full_lower[:3]
        name = _PROJ_ALIASES.get(key, full_lower)

    # Parse lon/lat — scalar (centre point) or 2-element (extent)
    # lon=None → defaults to full-world range for global projections.
    if lon is None:
        lon_arr = np.array([0.0])  # centre longitude only; projection decides range
    else:
        lon_arr = np.atleast_1d(np.asarray(lon, dtype=float)).ravel()
    lat_arr = np.atleast_1d(np.asarray(lat, dtype=float)).ravel()

    lon_mid = float(np.mean(lon_arr))
    lat_mid = float(np.mean(lat_arr))

    if name == 'equidistant':
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError(
                "m_proj('equidistant') requires lon=[lon_min, lon_max] and "
                "lat=[lat_min, lat_max]."
            )
        lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))

        proj = pyproj.Proj(proj='eqc', lat_ts=lat_mid, lon_0=lon_mid)
        corners_lon = [lon_lim[0], lon_lim[1], lon_lim[0], lon_lim[1]]
        corners_lat = [lat_lim[0], lat_lim[0], lat_lim[1], lat_lim[1]]
        xs, ys = proj(corners_lon, corners_lat)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_limits = (float(min(xs)), float(max(xs)))
        state.y_limits = (float(min(ys)), float(max(ys)))
        state.projection_type = 'rectangular'

    elif name == 'mercator':
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError(
                "m_proj('mercator') requires lon=[lon_min, lon_max] and "
                "lat=[lat_min, lat_max]."
            )
        lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))

        proj = pyproj.Proj(proj='merc', lon_0=lon_mid, lat_ts=0, R=_R_EARTH)
        corners_lon = [lon_lim[0], lon_lim[1], lon_lim[0], lon_lim[1]]
        corners_lat = [lat_lim[0], lat_lim[0], lat_lim[1], lat_lim[1]]
        xs, ys = proj(corners_lon, corners_lat)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_limits = (float(min(xs)), float(max(xs)))
        state.y_limits = (float(min(ys)), float(max(ys)))
        state.projection_type = 'rectangular'

    elif name == 'lambert':
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError(
                "m_proj('lambert') requires lon=[lon_min, lon_max] and "
                "lat=[lat_min, lat_max]."
            )
        lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))
        lat_span = lat_lim[1] - lat_lim[0]

        lat_1, lat_2 = _conic_standard_parallels(lat_mid, lat_span)
        proj = pyproj.Proj(
            proj='lcc', lat_1=lat_1, lat_2=lat_2, lat_0=lat_mid, lon_0=lon_mid
        )

        # Sample all 4 boundary edges to get the true projected extent
        n = 200
        b = np.linspace
        edge_lons = np.concatenate([
            b(lon_lim[0], lon_lim[1], n),   # bottom
            b(lon_lim[0], lon_lim[1], n),   # top
            np.full(n, lon_lim[0]),          # left
            np.full(n, lon_lim[1]),          # right
        ])
        edge_lats = np.concatenate([
            np.full(n, lat_lim[0]),
            np.full(n, lat_lim[1]),
            b(lat_lim[0], lat_lim[1], n),
            b(lat_lim[0], lat_lim[1], n),
        ])
        xs, ys = proj(edge_lons, edge_lats)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_limits = (float(np.min(xs)), float(np.max(xs)))
        state.y_limits = (float(np.min(ys)), float(np.max(ys)))
        state.projection_type = 'conic'

    elif name == 'albers':
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError(
                "m_proj('albers') requires lon=[lon_min, lon_max] and "
                "lat=[lat_min, lat_max]."
            )
        lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))
        lat_span = lat_lim[1] - lat_lim[0]
        lat_1, lat_2 = _conic_standard_parallels(lat_mid, lat_span)
        proj = pyproj.Proj(
            proj='aea', lat_1=lat_1, lat_2=lat_2, lat_0=lat_mid, lon_0=lon_mid
        )

        n = 200
        b = np.linspace
        edge_lons = np.concatenate([
            b(lon_lim[0], lon_lim[1], n),
            b(lon_lim[0], lon_lim[1], n),
            np.full(n, lon_lim[0]),
            np.full(n, lon_lim[1]),
        ])
        edge_lats = np.concatenate([
            np.full(n, lat_lim[0]),
            np.full(n, lat_lim[1]),
            b(lat_lim[0], lat_lim[1], n),
            b(lat_lim[0], lat_lim[1], n),
        ])
        xs, ys = proj(edge_lons, edge_lats)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_limits = (float(np.min(xs)), float(np.max(xs)))
        state.y_limits = (float(np.min(ys)), float(np.max(ys)))
        state.projection_type = 'conic'

    elif name == 'orthographic':
        # lon/lat are the centre of the hemisphere (scalar or 1-element)
        proj = pyproj.Proj(proj='ortho', lat_0=lat_mid, lon_0=lon_mid)

        state.projection_name = name
        state.proj = proj
        state.center_lat = lat_mid
        state.center_lon = lon_mid
        state.projection_type = 'circular'

        if radius is not None:
            # Zoom into a circular region of given angular radius (degrees).
            # Orthographic projected distance at angular offset r = R*sin(r).
            r = float(radius)
            proj_r = _R_EARTH * np.sin(np.radians(r))
            state.x_limits = (-proj_r, proj_r)
            state.y_limits = (-proj_r, proj_r)
            state.lon_limits = (lon_mid - r / max(np.cos(np.radians(lat_mid)), 0.01),
                                lon_mid + r / max(np.cos(np.radians(lat_mid)), 0.01))
            state.lat_limits = (lat_mid - r, lat_mid + r)
        else:
            state.lon_limits = (-180.0, 180.0)
            state.lat_limits = (-90.0, 90.0)
            state.x_limits = (-_R_EARTH, _R_EARTH)
            state.y_limits = (-_R_EARTH, _R_EARTH)

    elif name == 'stereographic':
        if radius is None:
            raise ValueError(
                "m_proj('stereographic') requires radius= in degrees "
                "(angular distance from the centre point to the map edge)."
            )
        radius = float(radius)
        lon_c = float(lon_arr[0])
        lat_c = float(lat_arr[0])

        proj = pyproj.Proj(proj='stere', lat_0=lat_c, lon_0=lon_c, R=_R_EARTH)

        # Projected radius: stereo formula  2·R·tan(r/2)
        projected_radius = 2.0 * _R_EARTH * np.tan(np.radians(radius) / 2.0)

        # Geographic bounding box of the visible cap
        lat_min_cap = float(np.clip(lat_c - radius, -90.0, 90.0))
        lat_max_cap = float(np.clip(lat_c + radius, -90.0, 90.0))

        state.projection_name = name
        state.lon_limits = (-180.0, 180.0)
        state.lat_limits = (lat_min_cap, lat_max_cap)
        state.proj = proj
        state.x_limits = (-projected_radius, projected_radius)
        state.y_limits = (-projected_radius, projected_radius)
        state.projection_type = 'circular'
        state.center_lat = lat_c
        state.center_lon = lon_c

    elif name in ('sinusoidal', 'mollweide'):
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError(
                f"m_proj('{name}') requires lon=[lon_min, lon_max] and "
                "lat=[lat_min, lat_max]."
            )
        lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))

        proj_key = 'sinu' if name == 'sinusoidal' else 'moll'
        proj = pyproj.Proj(proj=proj_key, lon_0=lon_mid, R=_R_EARTH)

        # Absolute x-offset for interrupted projections: the x-coordinate of
        # this lobe's central meridian in the global reference frame (lon_0=0).
        # Computed analytically to avoid pyproj's longitude wrapping at ±180°,
        # which would give wrong offsets for Pacific lobes (lon_mid > 180°).
        #
        # Sinusoidal at lat=0:   x = R * lon * pi/180
        # Mollweide at lat=0:    x = R * 2*sqrt(2)/pi * lon * pi/180
        #                          = R * 2*sqrt(2) * lon / 180
        lon_mid_rad = np.radians(lon_mid)
        if proj_key == 'sinu':
            x_offset = float(_R_EARTH * lon_mid_rad)
        else:  # mollweide
            x_offset = float(_R_EARTH * 2.0 * np.sqrt(2.0) * lon_mid_rad / np.pi)

        # Sample all 4 boundary edges to get the true projected extent
        n = 200
        b = np.linspace
        edge_lons = np.concatenate([
            b(lon_lim[0], lon_lim[1], n),
            b(lon_lim[0], lon_lim[1], n),
            np.full(n, lon_lim[0]),
            np.full(n, lon_lim[1]),
        ])
        edge_lats = np.concatenate([
            np.full(n, lat_lim[0]),
            np.full(n, lat_lim[1]),
            b(lat_lim[0], lat_lim[1], n),
            b(lat_lim[0], lat_lim[1], n),
        ])
        xs, ys = proj(edge_lons, edge_lats)
        xs = np.asarray(xs, dtype=float) + x_offset
        ys = np.asarray(ys, dtype=float)
        ok = np.isfinite(xs) & np.isfinite(ys)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_offset = x_offset
        state.x_limits = (float(np.min(xs[ok])), float(np.max(xs[ok])))
        state.y_limits = (float(np.min(ys[ok])), float(np.max(ys[ok])))
        state.projection_type = 'pseudocylindrical'

    elif name == 'oblique':
        # Oblique Mercator (Hotine cylindrical conformal).
        # Direct port of MATLAB m_map/private/mp_omerc.m (Snyder §9).
        # lat=[lat1, lat2], lon=[lon1, lon2] define two corner points.
        # aspect : x/y or y/x ratio (see direction).
        # direction : 'vertical' (default) — y-axis spans the two points;
        #             'horizontal' — x-axis spans the two points.
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError(
                "m_proj('oblique') requires lon=[lon1, lon2] and lat=[lat1, lat2]."
            )
        lat1, lat2 = float(lat_arr[0]), float(lat_arr[1])
        lon1, lon2 = float(lon_arr[0]), float(lon_arr[1])
        asp = float(aspect) if aspect is not None else 0.5
        is_vert = not str(direction).lower().startswith('h')

        r1, r2   = lat1 * np.pi/180, lat2 * np.pi/180
        rl1, rl2 = lon1 * np.pi/180, lon2 * np.pi/180

        # Poles of the oblique coordinate system (Snyder eq. 9-1 / 9-2)
        rpolelong = np.arctan2(
            np.cos(r1)*np.sin(r2)*np.cos(rl1) - np.sin(r1)*np.cos(r2)*np.cos(rl2),
            np.sin(r1)*np.cos(r2)*np.sin(rl2) - np.cos(r1)*np.sin(r2)*np.sin(rl1)
        )
        # tan(r1) is zero for a latitude limit on the equator, so clamp the
        # magnitude away from zero: the oblique pole is then at ±90°, which is
        # the correct limit, without a divide-by-zero warning en route.
        tan_r1 = np.tan(r1)
        if abs(tan_r1) < 1e-12:
            tan_r1 = 1e-12 if tan_r1 >= 0 else -1e-12
        rpolelat = np.arctan(-np.cos(rpolelong - rl1) / tan_r1)
        l0 = rpolelong + np.pi/2

        def _oblique_fwd(lon_deg, lat_deg,
                         _rpl=rpolelat, _l0=l0, _iv=is_vert):
            lo  = np.asarray(lon_deg, float) * np.pi/180 - _l0
            la  = np.asarray(lat_deg, float) * np.pi/180
            # Components of the geographic unit vector in the oblique frame:
            #   a3 = sin(oblique latitude), and the oblique longitude is the
            #   angle of (a1, a2).  mp_omerc.m forms that angle as
            #   arctan((tan(la)cos(rpl) + sin(rpl)sin(lo)) / cos(lo)); scaling
            #   both parts by cos(la) gives a1 and a2 below, so arctan2 is the
            #   same expression with the quadrant retained.  Plain arctan folds
            #   the far half of the oblique frame onto the near half, which makes
            #   the transform non-invertible — m_xy2ll then returns the antipode.
            a1 = np.cos(la) * np.cos(lo)
            a2 = (np.sin(la) * np.cos(_rpl)
                  + np.sin(_rpl) * np.cos(la) * np.sin(lo))
            A  = (np.sin(_rpl)*np.sin(la)
                  - np.cos(_rpl)*np.cos(la)*np.sin(lo))
            A  = np.clip(A, -1.0 + 1e-10, 1.0 - 1e-10)
            ang = np.arctan2(a2, a1)
            if _iv:
                yp = ang
                xp = -np.arctanh(A)
            else:
                xp = ang
                yp = np.arctanh(A)
            return xp * _R_EARTH, yp * _R_EARTH

        # Project the two corner points to determine map extent
        cx, cy = _oblique_fwd([lon1, lon2], [lat1, lat2])
        cx, cy = np.asarray(cx, float), np.asarray(cy, float)

        if is_vert:
            y_lo, y_hi = float(cy.min()), float(cy.max())
            half_x = (y_hi - y_lo) * asp / 2.0
            x_lo, x_hi = -half_x, half_x
        else:
            x_lo, x_hi = float(cx.min()), float(cx.max())
            half_y = (x_hi - x_lo) * asp / 2.0
            y_lo, y_hi = -half_y, half_y

        state.projection_name = name
        # state.proj is assigned below, once the inverse closure exists, so that
        # it can be wrapped in a forward+inverse callable (see _ObliqueProj).
        state.x_limits = (x_lo, x_hi)
        state.y_limits = (y_lo, y_hi)
        state.projection_type = 'oblique'

        # Compute the geographic extent of the projected map rectangle by
        # sampling many points along all four edges and inverting the transform.
        # This gives the true lon/lat range visible in the map (wider than just
        # the two corner points because the cross-track extent adds ≈half_x).
        n_edge = 200
        edge_x = np.concatenate([
            np.linspace(x_lo, x_hi, n_edge),   # bottom edge
            np.full(n_edge, x_hi),              # right edge
            np.linspace(x_hi, x_lo, n_edge),   # top edge
            np.full(n_edge, x_lo),              # left edge
        ])
        edge_y = np.concatenate([
            np.full(n_edge, y_lo),
            np.linspace(y_lo, y_hi, n_edge),
            np.full(n_edge, y_hi),
            np.linspace(y_hi, y_lo, n_edge),
        ])

        # Compute the true geographic extent of the projected map rectangle.
        # Method: same as m_map's mu_util('lllimits') — sample points along
        # all 4 edges of the xlims×ylims rectangle, convert back to lon/lat
        # using the analytical inverse (ported from mp_omerc.m xy2ll case).
        mean_lon = (lon1 + lon2) / 2.0
        n_edge = 31

        def _oblique_inv(x_m, y_m,
                         _rpl=rpolelat, _l0=l0, _iv=is_vert,
                         _mlon=mean_lon):
            """Inverse oblique Mercator (from mp_omerc.m 'xy2ll' case)."""
            xp = np.asarray(x_m, float) / _R_EARTH
            yp = np.asarray(y_m, float) / _R_EARTH
            if _iv:
                lat_rad = np.arcsin(
                    np.clip(
                        np.sin(_rpl) * np.tanh(-xp)
                        + np.cos(_rpl) * np.sin(yp) / np.cosh(-xp),
                        -1.0, 1.0)
                )
                lon_raw = (_l0 + np.arctan2(
                    np.sin(_rpl) * np.sin(yp) - np.cos(_rpl) * np.sinh(-xp),
                    np.cos(yp)
                )) * 180.0 / np.pi
            else:
                lat_rad = np.arcsin(
                    np.clip(
                        np.sin(_rpl) * np.tanh(yp)
                        + np.cos(_rpl) * np.sin(xp) / np.cosh(yp),
                        -1.0, 1.0)
                )
                lon_raw = (_l0 + np.arctan2(
                    np.sin(_rpl) * np.sin(xp) - np.cos(_rpl) * np.sinh(yp),
                    np.cos(xp)
                )) * 180.0 / np.pi
            lat_deg = lat_rad * 180.0 / np.pi
            # Wrap to within 180° of the mean input longitude (m_map approach)
            lon_deg = lon_raw - np.round((lon_raw - _mlon) / 360.0) * 360.0
            return lon_deg, lat_deg

        # Both directions available now — m_xy2ll needs the inverse.
        state.proj = _ObliqueProj(_oblique_fwd, _oblique_inv)

        # Sample all 4 edges of the projected rectangle (same as m_map m_box)
        t = np.linspace(0.0, 1.0, n_edge)
        bx = np.concatenate([
            x_lo + (x_hi - x_lo) * t,          # bottom
            np.full(n_edge, x_hi),              # right
            x_hi + (x_lo - x_hi) * t,          # top
            np.full(n_edge, x_lo),              # left
        ])
        by = np.concatenate([
            np.full(n_edge, y_lo),
            y_lo + (y_hi - y_lo) * t,
            np.full(n_edge, y_hi),
            y_hi + (y_lo - y_hi) * t,
        ])

        geo_lon, geo_lat = _oblique_inv(bx, by)
        finite = np.isfinite(geo_lon) & np.isfinite(geo_lat)
        if np.any(finite):
            state.lon_limits = (
                float(np.nanmin(geo_lon[finite])),
                float(np.nanmax(geo_lon[finite])),
            )
            state.lat_limits = (
                float(np.nanmin(geo_lat[finite])),
                float(np.nanmax(geo_lat[finite])),
            )
        else:
            state.lon_limits = (min(lon1, lon2), max(lon1, lon2))
            state.lat_limits = (min(lat1, lat2), max(lat1, lat2))

        # Wider geographic pre-filter for coast polygon clipping.
        # The oblique map rectangle extends well beyond the two corner points
        # in the cross-track direction.  Final clipping is done in projected
        # (x, y) space; the wide limits just avoid loading unnecessary polygons.
        cen_lon = (lon1 + lon2) / 2.0
        cen_lat = (lat1 + lat2) / 2.0
        buf_lon = max(abs(lon2 - lon1), 20.0) + 20.0
        buf_lat = max(abs(lat2 - lat1), 20.0) + 20.0
        state.coast_lon_limits = (
            float(np.clip(cen_lon - buf_lon, -180.0, 180.0)),
            float(np.clip(cen_lon + buf_lon, -180.0, 180.0)),
        )
        state.coast_lat_limits = (
            float(np.clip(cen_lat - buf_lat,  -90.0,  90.0)),
            float(np.clip(cen_lat + buf_lat,  -90.0,  90.0)),
        )

    elif name == 'azimuthal_equal_area':
        lon_c = float(lon_arr[0]) if lon is not None else 0.0
        lat_c = float(lat_arr[0])
        proj = pyproj.Proj(proj='laea', lat_0=lat_c, lon_0=lon_c, R=_R_EARTH)
        if radius is not None:
            r = float(radius)
            # LAEA projected radius at angular distance r: 2·R·sin(r/2)
            projected_radius = 2.0 * _R_EARTH * np.sin(np.radians(r) / 2.0)
            lat_min_cap = float(np.clip(lat_c - r, -90.0, 90.0))
            lat_max_cap = float(np.clip(lat_c + r, -90.0, 90.0))
        else:
            projected_radius = 2.0 * _R_EARTH
            lat_min_cap = -90.0
            lat_max_cap = 90.0
        state.projection_name = name
        state.proj = proj
        state.center_lat = lat_c
        state.center_lon = lon_c
        state.x_limits = (-projected_radius, projected_radius)
        state.y_limits = (-projected_radius, projected_radius)
        state.lon_limits = (-180.0, 180.0)
        state.lat_limits = (lat_min_cap, lat_max_cap)
        state.projection_type = 'circular'

    elif name == 'miller':
        # Miller cylindrical projection (modified Mercator, full-world capable).
        # lat: scalar → symmetric extent [-lat, lat]; [lat_min, lat_max] → explicit range.
        # lon: scalar or None → centre longitude (full world); [lon_min, lon_max] → regional.
        if len(lat_arr) == 1:
            lat_lim = (-float(lat_arr[0]), float(lat_arr[0]))
        else:
            lat_lim = (float(lat_arr.min()), float(lat_arr.max()))

        if lon is None or len(lon_arr) == 1:
            lon_lim = (-180.0, 180.0)
        else:
            lon_lim = (float(lon_arr.min()), float(lon_arr.max()))

        proj = pyproj.Proj(proj='mill', lon_0=lon_mid, R=_R_EARTH)

        corners_lon = [lon_lim[0], lon_lim[1], lon_lim[0], lon_lim[1]]
        corners_lat = [lat_lim[0], lat_lim[0], lat_lim[1], lat_lim[1]]
        xs, ys = proj(corners_lon, corners_lat)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_limits = (float(min(xs)), float(max(xs)))
        state.y_limits = (float(min(ys)), float(max(ys)))
        state.projection_type = 'rectangular'

    elif name == 'hammer':
        # Scalar lon → center longitude for a full-world map; None → 0°.
        # Two-element lon → explicit geographic limits with centre at midpoint.
        if lon is None or len(lon_arr) <= 1:
            clon = float(lon_arr[0]) if (lon is not None and len(lon_arr) == 1) else 0.0
            lon_lim = (-180.0, 180.0)
        else:
            lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
            clon = (lon_lim[0] + lon_lim[1]) / 2.0

        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))

        proj = pyproj.Proj(proj='hammer', lon_0=clon, R=_R_EARTH)

        # Sample boundaries to find true projected extent
        n = 360
        eq_lons = np.linspace(-180, 180, n)
        xs_eq, _ = proj(eq_lons, np.zeros(n))
        _, ys_lo = proj(np.zeros(n), np.full(n, lat_lim[0]))
        _, ys_hi = proj(np.zeros(n), np.full(n, lat_lim[1]))
        xs_eq = np.asarray(xs_eq, dtype=float)
        ys_lo = np.asarray(ys_lo, dtype=float)
        ys_hi = np.asarray(ys_hi, dtype=float)

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_offset = 0.0
        state.x_limits = (float(np.nanmin(xs_eq)), float(np.nanmax(xs_eq)))
        state.y_limits = (float(np.nanmin(ys_lo)), float(np.nanmax(ys_hi)))
        state.projection_type = 'pseudocylindrical'
        state.center_lon = clon

    elif name == 'robinson':
        # Pseudocylindrical world map.  MATLAB signature: m_proj('robinson','lon',[lo hi])
        # where [lo, hi] spans 360°.  The centre longitude is the midpoint.
        if lon is None or len(lon_arr) <= 1:
            clon = float(lon_arr[0]) if (lon is not None and len(lon_arr) == 1) else 0.0
            lon_lim = (-180.0, 180.0)
        else:
            # A 360° span (e.g. [-330, 30]) → full world centred at midpoint.
            span = float(lon_arr.max()) - float(lon_arr.min())
            clon = (float(lon_arr.min()) + float(lon_arr.max())) / 2.0
            if span >= 359.9:
                lon_lim = (clon - 180.0, clon + 180.0)
            else:
                lon_lim = (float(lon_arr.min()), float(lon_arr.max()))

        lat_lim_arr = np.atleast_1d(np.asarray(lat, dtype=float)).ravel()
        if len(lat_lim_arr) < 2:
            lat_lim = (-90.0, 90.0)
        else:
            lat_lim = (float(lat_lim_arr.min()), float(lat_lim_arr.max()))

        proj = pyproj.Proj(proj='robin', lon_0=clon, R=_R_EARTH)

        # Sample equator and pole-latitude lines to find projected extent
        n = 360
        eq_lons = np.linspace(clon - 180.0, clon + 180.0, n)
        xs_eq, _ = proj(eq_lons, np.zeros(n))
        _, ys_lo = proj(np.full(n, clon), np.linspace(lat_lim[0], lat_lim[1], n))
        xs_eq = np.asarray(xs_eq, dtype=float)
        ys_lo = np.asarray(ys_lo, dtype=float)

        # Robinson extends to ±_R_EARTH * ~0.5072 in y at poles; sample the poles directly
        _, y_bot = proj(clon, lat_lim[0])
        _, y_top = proj(clon, lat_lim[1])

        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_offset = 0.0
        # The linspace endpoints (clon±180°) both hit the pyproj discontinuity
        # and map to x_max, so nanmin underestimates |x_min|.  The Robinson
        # oval is symmetric about the centre meridian, so x_min = -x_max.
        _rob_x_max = float(np.nanmax(xs_eq))
        state.x_limits = (-_rob_x_max, _rob_x_max)
        state.y_limits = (float(min(y_bot, np.nanmin(ys_lo))), float(max(y_top, np.nanmax(ys_lo))))
        state.projection_type = 'pseudocylindrical'
        state.center_lon = clon

    elif name == 'utm':
        if len(lon_arr) < 2 or len(lat_arr) < 2:
            raise ValueError("m_proj('utm') requires lon=[lon_min, lon_max] and lat=[lat_min, lat_max].")
        lon_lim = (float(lon_arr.min()), float(lon_arr.max()))
        lat_lim = (float(lat_arr.min()), float(lat_arr.max()))
        zone = int((lon_mid + 180) / 6) + 1
        south = lat_mid < 0
        proj = pyproj.Proj(proj='utm', zone=zone, south=south, ellps='WGS84')
        corners_lon = [lon_lim[0], lon_lim[1], lon_lim[0], lon_lim[1]]
        corners_lat = [lat_lim[0], lat_lim[0], lat_lim[1], lat_lim[1]]
        xs, ys = proj(corners_lon, corners_lat)
        state.projection_name = name
        state.lon_limits = lon_lim
        state.lat_limits = lat_lim
        state.proj = proj
        state.x_limits = (float(min(xs)), float(max(xs)))
        state.y_limits = (float(min(ys)), float(max(ys)))
        state.projection_type = 'rectangular'
        state.utm_zone = zone
        state.utm_south = south

    else:
        raise NotImplementedError(
            f"Projection '{name}' is not yet implemented. "
            "Supported: 'equidistant', 'mercator', 'lambert', 'albers', 'orthographic', "
            "'stereographic', 'azimuthal equal-area', 'sinusoidal', 'mollweide', "
            "'oblique', 'miller', 'robinson', 'hammer', 'utm'."
        )


def m_ll2xy(lon, lat, *, clip: str = 'on'):
    """
    Convert geographic coordinates to map coordinates.

    Parameters
    ----------
    lon, lat : array-like
        Longitude and latitude in decimal degrees (broadcast-compatible).
    clip : {'on', 'off', 'patch'}
        'on'    — set out-of-bounds points to NaN.
        'off'   — no clipping.
        'patch' — same as 'on' (used by m_contourf).

    Returns
    -------
    x, y : np.ndarray
        Map coordinates in metres.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)

    x, y = state.proj(lon, lat)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    # Shift each lobe to its absolute position for interrupted pseudocylindrical maps.
    # Re-wrap afterwards: adding a Python float to a 0-d array yields a numpy
    # scalar, which is immutable and has no shape, and the clipping below needs
    # a real array for scalar as well as array input.
    if state.x_offset != 0.0:
        x = np.asarray(x + state.x_offset, dtype=float)

    if clip in ('on', 'patch'):
        if state.projection_type == 'circular':
            # Clip to the actual map disk.  For orthographic, R_map = R_EARTH and
            # back-hemisphere points already have x=inf so isfinite handles them.
            # For stereographic caps, we also need to reject finite points that
            # lie outside the cap circle (projected distance > R_map).
            R_map = float(state.x_limits[1])
            outside = ~(
                np.isfinite(x) & np.isfinite(y) &
                (x**2 + y**2 <= (R_map * 1.0005) ** 2)
            )
        elif state.projection_type == 'oblique':
            # Oblique Mercator: clip in projected (x, y) space, not lon/lat space,
            # because the map bounding box is defined in projected coordinates.
            outside = (
                ~np.isfinite(x) | ~np.isfinite(y) |
                (x < state.x_limits[0]) | (x > state.x_limits[1]) |
                (y < state.y_limits[0]) | (y > state.y_limits[1])
            )
        else:
            outside = (
                (lon < state.lon_limits[0]) | (lon > state.lon_limits[1]) |
                (lat < state.lat_limits[0]) | (lat > state.lat_limits[1])
            )
        if clip == 'on':
            # NaN-out coordinates outside the boundary (used for plotting lines/points).
            # np.where rather than masked item assignment so that 0-d input (a
            # plain-float call such as m_ll2xy(-123.0, 49.0)) works too.
            x = np.where(outside, np.nan, x)
            y = np.where(outside, np.nan, y)
        # clip='patch': keep raw coordinates; caller masks the data array instead.
        # This ensures contourf/contour receive a regular coordinate grid.

    return x, y


def m_xy2ll(x, y):
    """
    Convert map coordinates back to geographic coordinates.

    Parameters
    ----------
    x, y : array-like
        Map coordinates in metres.

    Returns
    -------
    lon, lat : np.ndarray
        Longitude and latitude in decimal degrees.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    lon, lat = state.proj(x, y, inverse=True)
    return np.asarray(lon, dtype=float), np.asarray(lat, dtype=float)
