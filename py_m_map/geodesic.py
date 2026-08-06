"""
Geodesic distance and position functions.

m_lldist   — great-circle distances (and optional geodesics) between waypoints
m_idist    — inverse geodesic: distance and azimuths between two points
m_fdist    — forward geodesic: endpoint given start, azimuth, and distance
m_xydist   — distance in projected map coordinates
"""
from __future__ import annotations
import numpy as np

_EARTH_RADIUS_KM = 6378.137  # matches m_lldist.m (WGS84 equatorial radius)

_ELLIPSOID_PARAMS: dict[str, tuple[float, float]] = {
    'normal': (1.0,        0.0),
    'sphere': (6370997.0,  0.0),
    'grs80':  (6378137.0,  1 / 298.257),
    'grs67':  (6378160.0,  1 / 298.247),
    'wgs84':  (6378137.0,  1 / 298.257223563),
    'wgs72':  (6378135.0,  1 / 298.260),
    'wgs66':  (6378145.0,  1 / 298.250),
    'wgs60':  (6378165.0,  1 / 298.300),
    'clrk66': (6378206.4,  1 / 294.980),
    'clrk80': (6378249.1,  1 / 293.466),
    'intl24': (6378388.0,  1 / 297.000),
    'intl67': (6378157.5,  1 / 298.250),
}


def _make_geod(spheroid: str):
    from pyproj import Geod
    key = spheroid.lower()
    if key not in _ELLIPSOID_PARAMS:
        raise ValueError(
            f"Unknown spheroid '{spheroid}'. Valid: {list(_ELLIPSOID_PARAMS)}"
        )
    a, f = _ELLIPSOID_PARAMS[key]
    return Geod(a=a, b=a) if f == 0.0 else Geod(a=a, f=f)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def m_lldist(lon, lat, N=None):
    """
    Spherical earth great-circle distances between successive waypoints.

    Parameters
    ----------
    lon, lat : array-like, shape (n,)
        Longitudes and latitudes in decimal degrees.
    N : int, optional
        If given, also compute N-point geodesics between successive points.

    Returns
    -------
    dist : ndarray, shape (n-1,)
        Distances in km between successive waypoints.
    lons, lats : ndarray, shape (n-1, N+1)   [only if N is given]
        Interpolated geodesic positions. Each row contains N+1 equally spaced
        points along the great circle from waypoint k to waypoint k+1.
    """
    p180 = np.pi / 180.0
    R = _EARTH_RADIUS_KM

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    m = len(lon) - 1

    lon1 = lon[:-1] * p180
    lon2 = lon[1:]  * p180
    lat1 = lat[:-1] * p180
    lat2 = lat[1:]  * p180

    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    angles = 2 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    dist = R * angles

    if N is None:
        return dist

    # N-point spherical geodesics via Cartesian unit vector interpolation
    v1 = np.column_stack([
        np.cos(lon1) * np.cos(lat1),
        np.sin(lon1) * np.cos(lat1),
        np.sin(lat1),
    ])
    v2 = np.column_stack([
        np.cos(lon2) * np.cos(lat2),
        np.sin(lon2) * np.cos(lat2),
        np.sin(lat2),
    ])

    n1 = np.cross(v1, v2)
    t1 = np.cross(n1, v1)
    norms = np.sqrt(np.sum(t1 ** 2, axis=1, keepdims=True))
    norms = np.where(norms < 1e-10, 1.0, norms)
    t1 = t1 / norms

    frac = np.linspace(0.0, 1.0, N + 1)
    lons_out = np.zeros((m, N + 1))
    lats_out = np.zeros((m, N + 1))

    for k in range(m):
        p = (v1[k, :, np.newaxis] * np.cos(angles[k] * frac) +
             t1[k, :, np.newaxis] * np.sin(angles[k] * frac))
        lons_out[k, :] = np.arctan2(p[1], p[0]) / p180
        lats_out[k, :] = np.arcsin(np.clip(p[2], -1.0, 1.0)) / p180

    return dist, lons_out, lats_out


def m_idist(lon1, lat1, lon2, lat2, spheroid: str = 'wgs84'):
    """
    Inverse geodesic: distance and azimuths between point pairs.

    Parameters
    ----------
    lon1, lat1 : float or array-like
        First point(s) in decimal degrees.
    lon2, lat2 : float or array-like
        Second point(s) in decimal degrees.
    spheroid : str
        Reference ellipsoid name (default 'wgs84').

    Returns
    -------
    s : float or ndarray
        Distance in **metres**.
    a12 : float or ndarray
        Forward azimuth from point 1 → point 2 (degrees, clockwise from north,
        in [0, 360)).
    a21 : float or ndarray
        Backward azimuth from point 2 → point 1 (degrees, in [0, 360)).
    """
    geod = _make_geod(spheroid)
    az12, az21, s = geod.inv(lon1, lat1, lon2, lat2)
    az12 = np.mod(np.asarray(az12, dtype=float), 360.0)
    az21 = np.mod(np.asarray(az21, dtype=float), 360.0)
    s = np.asarray(s, dtype=float)
    return s, az12, az21


def m_fdist(lon1, lat1, a12, s, spheroid: str = 'wgs84'):
    """
    Forward geodesic: endpoint given start point, azimuth, and distance.

    Parameters
    ----------
    lon1, lat1 : float or array-like
        Starting point(s) in decimal degrees.
    a12 : float or array-like
        Forward azimuth (degrees, clockwise from north).
    s : float or array-like
        Distance in **metres**.
    spheroid : str
        Reference ellipsoid name (default 'wgs84').

    Returns
    -------
    lon2, lat2 : float or ndarray
        Destination point(s) in decimal degrees.  Longitudes in [-180, 180].
    a21 : float or ndarray
        Backward azimuth from point 2 → point 1 (degrees, in [0, 360)).
    """
    geod = _make_geod(spheroid)
    lon2, lat2, a21_raw = geod.fwd(lon1, lat1, a12, s)
    a21 = np.mod(np.asarray(a21_raw, dtype=float), 360.0)
    return np.asarray(lon2, dtype=float), np.asarray(lat2, dtype=float), a21


def m_xydist(x, y):
    """
    Great-circle distances between successive points given in map coordinates.

    Inverse-projects `(x, y)` to lon/lat, then calls `m_lldist`.

    Parameters
    ----------
    x, y : array-like
        Map projection coordinates.

    Returns
    -------
    dist : ndarray, shape (n-1,)
        Distances in km between successive projected points.
    """
    from .projection import m_xy2ll
    lon, lat = m_xy2ll(x, y)
    return m_lldist(lon, lat)
