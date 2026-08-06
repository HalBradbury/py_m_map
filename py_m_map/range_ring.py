"""
Range rings centred on a geographic point: m_range_ring.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def m_range_ring(lon0: float, lat0: float, ranges,
                 *, npts: int = 360, **kwargs) -> None:
    """
    Draw great-circle range rings centred on (lon0, lat0).

    Parameters
    ----------
    lon0, lat0 : float
        Centre point in decimal degrees.
    ranges : array-like
        Ring radii in kilometres.
    npts : int
        Number of points per ring (default 360).
    **kwargs
        Passed to ax.plot() (e.g. color, linewidth, linestyle).
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    try:
        import pyproj
    except ImportError as exc:
        raise ImportError("pyproj is required for m_range_ring") from exc

    ranges_km = np.asarray(ranges, dtype=float).ravel()
    azimuths = np.linspace(0, 360, npts, endpoint=False)

    geod = pyproj.Geod(a=6378137.0, f=0)  # spherical earth

    ax = plt.gca()
    x_span = state.x_limits[1] - state.x_limits[0]

    kw = {'linewidth': 1, 'linestyle': '-'}
    kw.update(kwargs)

    for r_km in ranges_km:
        r_m = r_km * 1e3
        lons_r, lats_r, _ = geod.fwd(
            np.full(npts, lon0), np.full(npts, lat0),
            azimuths, np.full(npts, r_m),
        )
        lons_r = np.asarray(lons_r, dtype=float)
        lats_r = np.asarray(lats_r, dtype=float)

        # Close the ring
        lons_r = np.append(lons_r, lons_r[0])
        lats_r = np.append(lats_r, lats_r[0])

        x, y = m_ll2xy(lons_r, lats_r, clip='off')
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        # Insert NaN breaks at antimeridian/projection discontinuities
        dx = np.abs(np.diff(x))
        breaks = np.where(dx > 0.5 * x_span)[0] + 1
        x = np.insert(x, breaks, np.nan)
        y = np.insert(y, breaks, np.nan)

        ax.plot(x, y, **kw)
