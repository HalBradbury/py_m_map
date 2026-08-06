"""
m_quiver — plot velocity vectors on the current map projection.

Port of MATLAB m_map/m_quiver.m (Rich Pawlowicz, UBC EOAS).
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def m_quiver(lon, lat, u, v, *args, **kwargs):
    """
    Plot velocity vectors on the current map.

    Parameters
    ----------
    lon, lat : array-like
        Geographic positions (decimal degrees).  Must be the same shape.
    u, v : array-like
        Eastward and northward velocity components (same shape as lon/lat).
        Units are physical (e.g. m/s), not degrees/s.
    *args, **kwargs
        Passed directly to :func:`matplotlib.pyplot.quiver`.

    Returns
    -------
    h : QuiverKey
        The quiver handle (only when the caller captures it).

    Notes
    -----
    The vector components are rotated into map coordinates by computing
    local metric tensors via small finite-difference nudges in the
    eastward and northward directions — matching the MATLAB implementation.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    u   = np.asarray(u,   dtype=float)
    v   = np.asarray(v,   dtype=float)

    # Projected positions (NaN for out-of-bounds points)
    X, Y = m_ll2xy(lon, lat, clip='on')
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)

    # Local metric tensors: project two nearby points to find how map
    # coordinates change per degree East and per degree North.
    # Use a 0.001° nudge (same as MATLAB), scaled by 1000 so the arrow
    # components represent motion per 1 degree.
    flat = lon.ravel()
    flau = lat.ravel()

    # Northward nudge: (lon, lat) → (lon, lat+0.001)
    lons2 = np.stack([flat, flat], axis=1)         # (N, 2)
    lats2 = np.stack([flau, flau + 0.001], axis=1)
    XN, YN = m_ll2xy(lons2.ravel(), lats2.ravel(), clip='off')
    XN = np.asarray(XN, float).reshape(-1, 2)
    YN = np.asarray(YN, float).reshape(-1, 2)
    dXN = (XN[:, 1] - XN[:, 0]).reshape(lon.shape)
    dYN = (YN[:, 1] - YN[:, 0]).reshape(lon.shape)

    # Eastward nudge: (lon, lat) → (lon + 0.001/cos(lat), lat)
    cos_lat = np.cos(flau * np.pi / 180)
    cos_lat = np.where(np.abs(cos_lat) < 1e-6, 1e-6, cos_lat)
    lons3 = np.stack([flat, flat + 0.001 / cos_lat], axis=1)
    lats3 = np.stack([flau, flau], axis=1)
    XE, YE = m_ll2xy(lons3.ravel(), lats3.ravel(), clip='off')
    XE = np.asarray(XE, float).reshape(-1, 2)
    YE = np.asarray(YE, float).reshape(-1, 2)
    dXE = (XE[:, 1] - XE[:, 0]).reshape(lon.shape)
    dYE = (YE[:, 1] - YE[:, 0]).reshape(lon.shape)

    # Map velocity components: rotate u (east) and v (north) into (x, y)
    mU = u * dXE * 1000.0 + v * dXN * 1000.0
    mV = u * dYE * 1000.0 + v * dYN * 1000.0

    # Only plot where the base point is valid and u is finite
    ii = np.isfinite(X) & np.isfinite(u)

    ax = plt.gca()
    h = ax.quiver(X[ii], Y[ii], mU[ii], mV[ii], *args, **kwargs)
    return h
