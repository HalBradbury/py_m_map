"""
m_windbarb — plot meteorological wind barbs on the current map projection.

Port of MATLAB m_map/m_windbarb.m (Erye / Rich Pawlowicz, UBC EOAS).

Barbs are drawn as line segments in data (projected) coordinates so their
size scales naturally with the map, matching the MATLAB behaviour.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state

_UNIT_TO_KNOTS = {
    'knots': 1.0,
    'm/s': 1.0 / 0.5144,
    'kmh': 1.0 / 1.852,
    'mph': 1.0 / 1.151,
}

# Barb segment geometry in the local wind frame (+x = wind direction, +y = left)
# Each row: [[x0, y0], [x1, y1]]
_SEGS = np.array([
    [[-1.0,    0.], [-1.125,  0.325 ]],  # full barb 1
    [[-0.875,  0.], [-1.0,    0.325 ]],  # full barb 2
    [[-0.75,   0.], [-0.875,  0.325 ]],  # full barb 3
    [[-0.625,  0.], [-0.75,   0.325 ]],  # full barb 4
    [[-0.5,    0.], [-0.625,  0.325 ]],  # full barb 5
    [[-0.375,  0.], [-0.5,    0.325 ]],  # full barb 6
    [[-0.25,   0.], [-0.375,  0.325 ]],  # full barb 7
    [[-0.125,  0.], [-0.25,   0.325 ]],  # full barb 8
    [[-0.875,  0.], [-0.9375, 0.1625]],  # half barb 2
    [[-0.75,   0.], [-0.8125, 0.1625]],  # half barb 3
    [[-0.625,  0.], [-0.6875, 0.1625]],  # half barb 4
    [[-0.5,    0.], [-0.5625, 0.1625]],  # half barb 5
    [[-0.375,  0.], [-0.4375, 0.1625]],  # half barb 6
    [[-0.25,   0.], [-0.3125, 0.1625]],  # half barb 7
    [[-0.125,  0.], [-0.1875, 0.1625]],  # half barb 8
    [[-1.0,    0.], [-0.875,  0.325 ]],  # pennant slant 1
    [[-0.75,   0.], [-0.625,  0.325 ]],  # pennant slant 2
    [[ 0.0,    0.], [-1.0,    0.0   ]],  # base shaft (always drawn)
], dtype=float)  # shape (18, 2, 2)


def _masks(umag):
    """Return 18 boolean arrays selecting which barb elements to draw."""
    return [
        (umag >  7.5) & (umag <= 47.5),
        (umag > 17.5) & (umag <= 47.5),
        (umag > 27.5),
        ((umag > 37.5) & (umag <= 47.5)) | ((umag > 57.5) & (umag <= 97.5)),
        (umag > 67.5),
        ((umag > 77.5) & (umag <  97.5)) | (umag > 107.5),
        ((umag > 87.5) & (umag <  97.5)) | (umag > 117.5),
        (umag > 127.5),
        ((umag >  2.5) & (umag <=  7.5)) | ((umag > 12.5) & (umag <= 17.5)),
        (umag > 22.5) & (umag <= 27.5),
        ((umag > 32.5) & (umag <= 37.5)) | ((umag > 52.5) & (umag <= 57.5)),
        ((umag > 42.5) & (umag <= 47.5)) | ((umag > 62.5) & (umag <= 67.5)),
        ((umag > 72.5) & (umag <= 77.5)) | ((umag > 102.5) & (umag <= 107.5)),
        ((umag > 82.5) & (umag <= 87.5)) | ((umag > 112.5) & (umag <= 117.5)),
        ((umag > 92.5) & (umag <= 97.5)) | ((umag > 122.5) & (umag <= 127.5)),
        (umag > 47.5),
        (umag > 97.5),
        (umag >  0.0),
    ]


def m_windbarb(lon, lat, u, v, scale=0.9, *, units='knots', **kwargs):
    """
    Plot wind barbs on the current map.

    Parameters
    ----------
    lon, lat : array-like
        Geographic positions (decimal degrees).
    u, v : array-like
        Eastward and northward wind components (same shape as lon/lat).
    scale : float
        Barb-length scaling relative to average grid column spacing.
        Default 0.9; Pawlowicz's sat_ex5 example uses 2.
    units : {'knots', 'm/s', 'kmh', 'mph'}
        Units of u/v; controls the barb-count symbology.
    **kwargs
        Passed to :func:`matplotlib.axes.Axes.plot` (e.g. ``color='r'``,
        ``linewidth=1``).

    Returns
    -------
    line : matplotlib.lines.Line2D or None
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    u   = np.asarray(u,   dtype=float)
    v   = np.asarray(v,   dtype=float)

    scf = _UNIT_TO_KNOTS.get(units.lower(), 1.0)

    X, Y = m_ll2xy(lon, lat, clip='on')
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)

    flat = lon.ravel()
    flau = lat.ravel()

    # Northward finite-difference displacement in map space (×1000 to un-nudge)
    lons2 = np.stack([flat, flat         ], axis=1)
    lats2 = np.stack([flau, flau + 0.001 ], axis=1)
    XN, YN = m_ll2xy(lons2.ravel(), lats2.ravel(), clip='off')
    XN = np.asarray(XN, float).reshape(-1, 2)
    YN = np.asarray(YN, float).reshape(-1, 2)
    dXN = ((XN[:, 1] - XN[:, 0]) * 1000).reshape(lon.shape)
    dYN = ((YN[:, 1] - YN[:, 0]) * 1000).reshape(lon.shape)

    # Eastward finite-difference displacement in map space (×1000 to un-nudge)
    cos_lat = np.cos(flau * np.pi / 180)
    cos_lat = np.where(np.abs(cos_lat) < 1e-6, 1e-6, cos_lat)
    lons3 = np.stack([flat, flat + 0.001 / cos_lat], axis=1)
    lats3 = np.stack([flau, flau                  ], axis=1)
    XE, YE = m_ll2xy(lons3.ravel(), lats3.ravel(), clip='off')
    XE = np.asarray(XE, float).reshape(-1, 2)
    YE = np.asarray(YE, float).reshape(-1, 2)
    dXE = ((XE[:, 1] - XE[:, 0]) * 1000).reshape(lon.shape)
    dYE = ((YE[:, 1] - YE[:, 0]) * 1000).reshape(lon.shape)

    # Map-coordinate wind vector (not normalised — only direction is used)
    mU = u * dXE + v * dXN
    mV = u * dYE + v * dYN

    umag  = np.sqrt(u**2 + v**2) * scf  # physical wind speed in knots
    theta = np.arctan2(mV, mU)          # wind direction in map space

    # Barb length = scale × average column spacing (mirrors MATLAB scale2 formula)
    _, n_cols = (X.shape if X.ndim == 2 else (1, X.size))
    x_range = np.nanmax(X) - np.nanmin(X)
    scale2 = scale * x_range / max(n_cols, 1)

    valid = np.isfinite(X) & np.isfinite(umag) & (umag > 0)
    masks = _masks(umag)

    Ax, Ay = [], []
    ct_all = np.cos(theta.ravel())
    st_all = np.sin(theta.ravel())
    Xv = X.ravel()
    Yv = Y.ravel()

    for mask, seg in zip(masks, _SEGS):
        ii = (mask & valid).ravel()
        if not ii.any():
            continue
        ct, st = ct_all[ii], st_all[ii]
        xi, yi = Xv[ii], Yv[ii]

        # Rotate both endpoints from local frame to map frame, then translate
        x0 = (seg[0, 0]*ct - seg[0, 1]*st) * scale2 + xi
        y0 = (seg[0, 0]*st + seg[0, 1]*ct) * scale2 + yi
        x1 = (seg[1, 0]*ct - seg[1, 1]*st) * scale2 + xi
        y1 = (seg[1, 0]*st + seg[1, 1]*ct) * scale2 + yi

        nans = np.full(x0.shape, np.nan)
        Ax.append(np.column_stack([x0, x1, nans]).ravel())
        Ay.append(np.column_stack([y0, y1, nans]).ravel())

    ax = plt.gca()
    if Ax:
        h, = ax.plot(np.concatenate(Ax), np.concatenate(Ay), **kwargs)
        return h
    return None
