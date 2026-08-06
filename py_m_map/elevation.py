"""
Built-in 1-degree global topography/bathymetry.

m_elev — ported from m_elev.m.  Where MATLAB m_map reads its private m_topo.mat,
this uses an equivalent grid bundled with the package (see _BUNDLED_TOPO).
"""
from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from ._state import get_state
from .contour import m_contourf, m_contour

#: Bundled 1° global topography, shipped inside the package so m_elev works with
#: no setup.  Derived by 1° block-averaging ETOPO1 (Amante & Eakins, 2009, NOAA
#: NGDC) — a US Government work, hence redistributable.  It agrees with the
#: MATLAB m_map m_topo.mat grid to 8 m RMS (correlation 1.00000), so figures are
#: interchangeable with the original for practical purposes.
_BUNDLED_TOPO = Path(__file__).resolve().parent / 'data' / 'topo_1deg.npz'

#: Set to a .npz (key 'topo') or MATLAB .mat (key 'topo') holding a 180×360 grid
#: to override the bundled data — e.g. m_map's own m_topo.mat for exact parity.
_TOPO_ENV_VAR = 'PY_M_MAP_TOPO_FILE'

_topo_cache: np.ndarray | None = None


def _load_topo() -> np.ndarray:
    """
    Lazy-load the 180×360 topography grid.

    The bundled ETOPO1-derived grid is used unless PY_M_MAP_TOPO_FILE points
    elsewhere.  The bundled file is preferred by default rather than any
    m_topo.mat that happens to sit beside the package, so that the same code
    produces the same figures on every machine.
    """
    global _topo_cache
    if _topo_cache is not None:
        return _topo_cache

    override = os.environ.get(_TOPO_ENV_VAR, '')
    path = Path(override).expanduser() if override else _BUNDLED_TOPO

    if not path.is_file():
        raise FileNotFoundError(
            f"m_elev topography grid not found at {path}."
            + (f"\n  {_TOPO_ENV_VAR} is set to {override!r} — check the path."
               if override else
               "\n  The bundled grid is missing, which means the installation is "
               "incomplete; reinstall py_m_map, or set "
               f"{_TOPO_ENV_VAR} to a 180x360 topography file.")
        )

    if path.suffix == '.npz':
        with np.load(path) as d:
            topo = d['topo']
    else:
        import scipy.io
        topo = scipy.io.loadmat(str(path))['topo']

    topo = np.asarray(topo, dtype=float)
    if topo.shape != (180, 360):
        raise ValueError(
            f"m_elev expects a 180x360 topography grid, got {topo.shape} "
            f"from {path}."
        )
    _topo_cache = topo
    return _topo_cache


def _extract_topo(state) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract the topo sub-array covering the current map extent.

    Returns
    -------
    lons : 1-D array  (decimal degrees, –180 … 180 convention)
    lats : 1-D array  (decimal degrees, –89.5 … 89.5)
    Z    : 2-D array  shape (len(lats), len(lons))
    """
    topo = _load_topo()

    # Grid centre positions
    # Row i → lat  = i − 89.5°   (i=0 → −89.5, i=179 → 89.5)
    # Col j → lon₃₆₀ = j + 0.5°  (0–360 convention)
    lats_full = np.arange(-89.5, 90.0, 1.0)         # 180 values
    lons_360_full = np.arange(0.5, 360.0, 1.0)       # 360 values

    lat_min, lat_max = state.lat_limits
    lon_min, lon_max = state.lon_limits

    # Latitude indices (expand by 1° so contours reach the map edge)
    ilat = np.where(
        (lats_full >= lat_min - 1.0) & (lats_full <= lat_max + 1.0)
    )[0]

    # Longitude indices — work in 0–360 space
    def _to_360(lon: float) -> float:
        return lon + 360.0 if lon < 0.0 else lon

    lo360_min = _to_360(lon_min) - 1.0
    lo360_max = _to_360(lon_max) + 1.0

    if lon_max - lon_min >= 359.0:
        # Full global longitude coverage (e.g. circular/polar projections)
        ilon = np.arange(len(lons_360_full))
    elif lo360_min <= lo360_max:
        # Contiguous range in 0–360 (e.g. Western Hemisphere, Asia–Pacific)
        ilon = np.where(
            (lons_360_full >= lo360_min) & (lons_360_full <= lo360_max)
        )[0]
    else:
        # Wraps across 0° / 360° (e.g. North Atlantic spanning prime meridian)
        ilon = np.where(
            (lons_360_full >= lo360_min) | (lons_360_full <= lo360_max)
        )[0]

    lats_out = lats_full[ilat]
    lons_360_out = lons_360_full[ilon]
    # Convert to –180 … 180
    lons_out = np.where(lons_360_out > 180.0, lons_360_out - 360.0, lons_360_out)

    Z = topo[np.ix_(ilat, ilon)]

    # When the selection wraps across the prime meridian (0°/360°), the ilon
    # indices are not in ascending longitude order (e.g. [0,1,...,20, 348,...,359])
    # which produces a jump from positive to negative longitudes in lons_out.
    # Sort columns by ascending longitude so the meshgrid is contiguous.
    sort_idx = np.argsort(lons_out)
    if not np.all(sort_idx == np.arange(len(sort_idx))):
        lons_out = lons_out[sort_idx]
        Z = Z[:, sort_idx]

    # For global longitude coverage, pad one column at each edge by wrapping
    # so that interpolators queried near ±180° don't return NaN.
    if lon_max - lon_min >= 359.0:
        lons_out = np.concatenate([[lons_out[0] - 1.0], lons_out, [lons_out[-1] + 1.0]])
        Z = np.hstack([Z[:, [-1]], Z, Z[:, [0]]])

    return lons_out, lats_out, Z


def m_elev(
    mode: str = 'contourf',
    levels=None,
    upsample: int = 1,
    **kwargs,
):
    """
    Draw topography / bathymetry from the 1-degree ETOPO1-derived database.

    Parameters
    ----------
    mode : {'contourf', 'contour', 'shadedrelief'}
        Type of plot.
    levels : array-like or None
        Contour levels.  Default: 1000 m intervals from −7000 to +5000 m.
    upsample : int
        Spatial upsampling factor applied via bicubic spline before plotting.
        Default 1 (no upsampling).  Use 4–8 for regional maps to smooth the
        1-degree source data.
    **kwargs
        Forwarded to the underlying plotting function
        (``m_contourf``, ``m_contour``, or ``m_shadedrelief``).

    Returns
    -------
    The return value of the underlying plotting function.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lons, lats, Z = _extract_topo(state)

    if upsample > 1:
        from scipy.interpolate import RectBivariateSpline
        interp = RectBivariateSpline(lats, lons, Z, kx=3, ky=3)
        lats = np.linspace(lats[0], lats[-1], len(lats) * upsample)
        lons = np.linspace(lons[0], lons[-1], len(lons) * upsample)
        Z = interp(lats, lons)

    if levels is None:
        levels = np.concatenate([
            np.arange(-7000, -999, 1000),
            np.arange(1000, 5001, 1000),
        ])
    else:
        levels = np.asarray(levels, dtype=float)

    if mode == 'contourf':
        return m_contourf(lons, lats, Z, levels, **kwargs)
    elif mode == 'contour':
        return m_contour(lons, lats, Z, levels, **kwargs)
    elif mode == 'shadedrelief':
        from .shaded_relief import m_shadedrelief
        return m_shadedrelief(lons, lats, Z, **kwargs)
    elif mode == 'image':
        from .image import m_image
        return m_image(lons, lats, Z, **kwargs)
    else:
        raise ValueError(f"m_elev: unrecognised mode '{mode}' (choose 'contourf', 'contour', 'shadedrelief', or 'image').")
