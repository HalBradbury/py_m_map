"""
Filled and line contours on a map.

m_contourf — filled contours (ported from m_contourf.m)
m_contour  — contour lines  (ported from m_contour.m)
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.transforms import Bbox, TransformedBbox
from .projection import m_ll2xy
from ._state import get_state


def _clip_cs_to_map(cs, state, ax):
    """
    Clip a QuadContourSet to the map boundary rectangle.

    In matplotlib ≥ 3.8, QuadContourSet is a single artist; set_clip_box()
    with a TransformedBbox is the correct way to restrict its rendering to a
    data-coordinate rectangle.
    """
    x0, x1 = state.x_limits
    y0, y1 = state.y_limits
    clip_bbox = TransformedBbox(Bbox([[x0, y0], [x1, y1]]), ax.transData)
    cs.set_clip_box(clip_bbox)


def m_contourf(lon, lat, data, levels=None, **kwargs):
    """
    Draw filled contours on the current map.

    Parameters
    ----------
    lon : 1-D array-like
        Longitude vector in decimal degrees.
    lat : 1-D array-like
        Latitude vector in decimal degrees.
    data : 2-D array-like, shape (len(lat), len(lon))
        Data values to contour.
    levels : array-like or int, optional
        Contour levels passed to ax.contourf.
    **kwargs
        Additional keyword arguments passed to ax.contourf (e.g. cmap, norm).

    Returns
    -------
    matplotlib.contour.QuadContourSet
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    data = np.asarray(data, dtype=float)

    # Expand 1-D coordinate vectors to 2-D grids
    if lon.ndim == 1 and lat.ndim == 1:
        lon2d, lat2d = np.meshgrid(lon, lat)
    else:
        lon2d, lat2d = lon, lat

    # Project with clipping to locate out-of-bounds points
    X, Y = m_ll2xy(lon2d, lat2d, clip='on')
    outside = np.isnan(X)

    # Mark out-of-bounds data as NaN
    data = data.copy()
    data[outside] = np.nan

    # Reproject without NaN coordinates — contourf cannot handle NaN x/y
    if np.any(outside):
        X, Y = m_ll2xy(lon2d, lat2d, clip='patch')

    # Pop MATLAB edgecolor kwarg — controls overlay contour lines on contourf.
    # 'none' suppresses lines; any other value overrides the default black.
    edgecolor = kwargs.pop('edgecolor', None)
    no_overlay_lines = (edgecolor is not None and str(edgecolor).lower() == 'none')

    ax = plt.gca()
    if levels is not None:
        cs = ax.contourf(X, Y, data, levels, **kwargs)
    else:
        cs = ax.contourf(X, Y, data, **kwargs)

    # Draw contour lines on top, matching MATLAB contourf behaviour.
    # Suppressed when edgecolor='none' is passed (MATLAB compat).
    if not no_overlay_lines:
        line_color = edgecolor if edgecolor is not None else 'k'
        line_kw = {k: v for k, v in kwargs.items()
                   if k not in ('cmap', 'norm', 'alpha', 'hatches', 'extend',
                                'vmin', 'vmax', 'antialiased')}
        lvls = cs.levels
        cs_lines = ax.contour(X, Y, data, lvls, colors=line_color,
                              linewidths=0.4, **line_kw)

    # Clip contours to the map boundary rectangle for bounded projections.
    if state.projection_type in ('oblique', 'rectangular'):
        _clip_cs_to_map(cs, state, ax)
        if not no_overlay_lines:
            _clip_cs_to_map(cs_lines, state, ax)

    return cs


def m_contour(lon, lat, data, levels=None, **kwargs):
    """
    Draw contour lines on the current map.

    Parameters
    ----------
    lon, lat, data : same as m_contourf.
    levels : array-like or int, optional
    **kwargs : passed to ax.contour.

    Returns
    -------
    matplotlib.contour.QuadContourSet
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    data = np.asarray(data, dtype=float)

    # MATLAB uses 'edgecolor' for contour line colour; map to matplotlib 'colors'
    if 'edgecolor' in kwargs and 'colors' not in kwargs:
        kwargs = dict(kwargs)
        kwargs['colors'] = kwargs.pop('edgecolor')

    # matplotlib dashes negative contours by default; match MATLAB's solid-line behaviour
    kwargs.setdefault('linestyles', '-')

    if lon.ndim == 1 and lat.ndim == 1:
        lon2d, lat2d = np.meshgrid(lon, lat)
    else:
        lon2d, lat2d = lon, lat

    X, Y = m_ll2xy(lon2d, lat2d, clip='on')
    outside = np.isnan(X)
    data = data.copy()
    data[outside] = np.nan
    if np.any(outside):
        X, Y = m_ll2xy(lon2d, lat2d, clip='patch')

    ax = plt.gca()
    if levels is not None:
        cs = ax.contour(X, Y, data, levels, **kwargs)
    else:
        cs = ax.contour(X, Y, data, **kwargs)

    # Clip contours to the map boundary rectangle for bounded projections.
    if state.projection_type in ('oblique', 'rectangular'):
        _clip_cs_to_map(cs, state, ax)

    return cs
