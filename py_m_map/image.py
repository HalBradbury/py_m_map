"""
m_image — reproject a lon/lat-gridded raster image onto the map projection.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_xy2ll
from ._state import get_state


def m_image(lon, lat, C, *, resolution=1000, **kwargs):
    """
    Display a raster image (or scalar field) gridded in geographic coordinates.

    The image is inverse-projected onto a regular grid in map coordinates
    and displayed via ``ax.imshow`` with the correct spatial extent.

    Parameters
    ----------
    lon, lat : array-like, shape (N,) or (2,)
        Longitude / latitude coordinates of the image columns / rows.
        A 2-element vector is treated as ``[lo, hi]`` with even spacing.
        Longitudes must be monotonically increasing (no 180→−180 wrap).
    C : array-like
        Image data.  Supported shapes and dtypes:

        * ``(M, N)`` float/int — scalar field; bilinear interpolation;
          out-of-map pixels become NaN (transparent).
        * ``(M, N, 3)`` uint8 — true-colour RGB; nearest-neighbour
          interpolation; out-of-map pixels become transparent.
        * ``(M, N, 4)`` uint8 — true-colour RGBA; input alpha channel respected.

    resolution : int or (int, int), optional
        Output pixel dimensions ``(nx, ny)``.  Default 1000.
    **kwargs
        Forwarded to ``ax.imshow``.  ``origin`` defaults to ``'lower'``;
        ``aspect`` defaults to ``'auto'``; ``interpolation`` defaults to
        ``'none'``.

    Returns
    -------
    h : AxesImage
    """
    from scipy.interpolate import RegularGridInterpolator

    state = get_state()

    lon = np.asarray(lon, dtype=float).ravel()
    lat = np.asarray(lat, dtype=float).ravel()
    C = np.asarray(C)

    if len(lon) == 2:
        lon = np.linspace(lon[0], lon[1], C.shape[1])
    if len(lat) == 2:
        lat = np.linspace(lat[0], lat[1], C.shape[0])

    # Ensure monotonically increasing for RegularGridInterpolator
    if lat[-1] < lat[0]:
        lat = lat[::-1].copy()
        C = C[::-1].copy()
    if lon[-1] < lon[0]:
        lon = lon[::-1].copy()
        C = C[:, ::-1].copy()

    if isinstance(resolution, (int, float)):
        nx = ny = int(resolution)
    else:
        nx, ny = int(resolution[0]), int(resolution[1])

    # Regular grid in projected map coordinates
    xlm = np.linspace(float(state.x_limits[0]), float(state.x_limits[1]), nx)
    ylm = np.linspace(float(state.y_limits[0]), float(state.y_limits[1]), ny)
    XX, YY = np.meshgrid(xlm, ylm)

    HLG, HLT = m_xy2ll(XX, YY)
    pts = np.stack([HLT.ravel(), HLG.ravel()], axis=1)

    # Pixels outside the map boundary (non-rectangular projections)
    if state.projection_type == 'circular':
        R_map = float(state.x_limits[1])
        outside = (XX**2 + YY**2) > R_map**2
    else:
        outside = (
            ~np.isfinite(HLT) | ~np.isfinite(HLG) |
            (HLT < state.lat_limits[0]) | (HLT > state.lat_limits[1]) |
            (HLG < state.lon_limits[0]) | (HLG > state.lon_limits[1])
        )

    is_rgb = C.ndim == 3

    if is_rgb:
        n_chan = C.shape[2]
        is_uint8 = (C.dtype == np.uint8)
        method = 'nearest' if is_uint8 else 'linear'

        channels = []
        for k in range(n_chan):
            interp = RegularGridInterpolator(
                (lat, lon), C[:, :, k].astype(float),
                method=method, bounds_error=False,
                fill_value=255.0 if is_uint8 else np.nan,
            )
            channels.append(interp(pts).reshape(ny, nx))

        if n_chan == 3:
            # Append alpha channel: 0 outside map, 255 (or 1.0) inside
            alpha_ch = np.where(outside, 0.0, 255.0 if is_uint8 else 1.0)
            channels.append(alpha_ch)

        GI = np.stack(channels, axis=2)
        if is_uint8:
            GI = np.clip(GI, 0, 255).astype(np.uint8)
            GI[outside, 3] = 0
        else:
            GI[outside, -1] = 0.0

    else:
        interp = RegularGridInterpolator(
            (lat, lon), C.astype(float),
            method='linear', bounds_error=False, fill_value=np.nan,
        )
        GI = interp(pts).reshape(ny, nx)
        GI[outside] = np.nan

    extent = [
        float(state.x_limits[0]), float(state.x_limits[1]),
        float(state.y_limits[0]), float(state.y_limits[1]),
    ]

    kwargs.setdefault('origin', 'lower')
    kwargs.setdefault('aspect', 'auto')
    kwargs.setdefault('interpolation', 'none')

    ax = plt.gca()
    return ax.imshow(GI, extent=extent, **kwargs)
