"""
Geographic line and point plotting on a map.

m_line — ported from m_line.m
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def m_line(lon, lat, **kwargs):
    """
    Plot a line (or points) on the current map.

    Parameters
    ----------
    lon, lat : array-like
        Geographic coordinates in decimal degrees.
    **kwargs
        Forwarded to ``ax.plot()``.  Common keys: ``color``, ``linewidth``,
        ``linestyle``, ``marker``, ``markersize``.

    Returns
    -------
    list of matplotlib.lines.Line2D
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float).ravel()
    lat = np.asarray(lat, dtype=float).ravel()

    x, y = m_ll2xy(lon, lat, clip='off')
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    invalid = ~(np.isfinite(x) & np.isfinite(y))
    x[invalid] = np.nan
    y[invalid] = np.nan

    ax = plt.gca()
    return ax.plot(x, y, **kwargs)
