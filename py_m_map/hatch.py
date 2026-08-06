"""
Hatch lines and speckle fills for geographic polygons: m_hatch.

Ported from m_hatch.m (R. Pawlowicz, UBC EOAS).
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def m_hatch(lon, lat, style: str = 'single', angle: float = 45,
            step: float = 10, **kwargs) -> None:
    """
    Draw hatch lines or speckle inside a geographic polygon.

    Parameters
    ----------
    lon, lat : array-like
        Polygon vertices in decimal degrees (closed or open ring).
    style : {'single', 'cross', 'speckle', 'outspeckle'}
        'single'     — parallel hatch lines at *angle* degrees.
        'cross'      — cross-hatch (angle and angle+90 degrees).
        'speckle'    — dots scattered within *angle* pts of boundary (inward).
        'outspeckle' — dots scattered outside boundary.
    angle : float
        Hatch angle in degrees (single/cross) or scatter half-width in
        points (speckle/outspeckle).
    step : float
        Hatch line spacing (single/cross) or dot spacing (speckle) in points.
    **kwargs
        Forwarded to ``ax.plot()``.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float).ravel()
    lat = np.asarray(lat, dtype=float).ravel()

    x, y = m_ll2xy(lon, lat, clip='off')
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    ax = plt.gca()
    _hatch_xy(ax, x, y, style, angle, step, **kwargs)


def _hatch_xy(ax, x, y, style: str, angle: float, step: float, **kwargs) -> None:
    """Hatch/speckle on already-projected (map-coordinate) polygon."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x, y = x[valid], y[valid]
    if len(x) < 3:
        return
    if x[0] != x[-1] or y[0] != y[-1]:
        x = np.append(x, x[0])
        y = np.append(y, y[0])

    if style in ('single', 'cross'):
        _draw_hatch_lines(ax, x, y, angle, step, **kwargs)
        if style == 'cross':
            _draw_hatch_lines(ax, x, y, angle + 90.0, step, **kwargs)
    else:
        _draw_speckle(ax, x, y, angle, step,
                      outward=(style == 'outspeckle'), **kwargs)


def _get_pts_per_data(ax):
    """Return (pts_per_xdata, pts_per_ydata) using the map projection extent."""
    fig = ax.get_figure()
    fig_w, fig_h = fig.get_size_inches()
    pos = ax.get_position()
    ax_w_pts = pos.width * fig_w * 72.0
    ax_h_pts = pos.height * fig_h * 72.0
    # Use the projection state limits (not ax auto-scale, which can be
    # inflated by out-of-bounds clip='off' points from coastline drawing).
    state = get_state()
    if state.proj is not None:
        x_span = state.x_limits[1] - state.x_limits[0]
        y_span = state.y_limits[1] - state.y_limits[0]
    else:
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_span = xlim[1] - xlim[0]
        y_span = ylim[1] - ylim[0]
    pts_x = ax_w_pts / x_span if x_span > 0 else 1.0
    pts_y = ax_h_pts / y_span if y_span > 0 else 1.0
    return pts_x, pts_y


def _draw_hatch_lines(ax, x, y, angle_deg: float, step: float, **kwargs) -> None:
    """Scan-line hatch inside polygon using uniform point-space density."""
    pts_x, pts_y = _get_pts_per_data(ax)

    xs = x * pts_x
    ys = y * pts_y

    a = np.radians(angle_deg)
    ca, sa = np.cos(a), np.sin(a)
    xr = xs * ca + ys * sa
    yr = -xs * sa + ys * ca

    yr_min, yr_max = np.nanmin(yr), np.nanmax(yr)
    levels = np.arange(np.ceil(yr_min / step) * step,
                       yr_max + step * 0.5, step)

    kw = {'linewidth': 0.5}
    kw.update(kwargs)

    n = len(xr)
    for lev in levels:
        crossings: list[float] = []
        for i in range(n - 1):
            y0i, y1i = yr[i], yr[i + 1]
            if np.isnan(y0i) or np.isnan(y1i):
                continue
            if (y0i <= lev < y1i) or (y1i <= lev < y0i):
                t = (lev - y0i) / (y1i - y0i)
                crossings.append(float(xr[i] + t * (xr[i + 1] - xr[i])))
        crossings.sort()
        for j in range(0, len(crossings) - 1, 2):
            x0r, x1r = crossings[j], crossings[j + 1]
            # Inverse rotation back to scaled data coords
            x0s = x0r * ca - lev * sa
            y0s = x0r * sa + lev * ca
            x1s = x1r * ca - lev * sa
            y1s = x1r * sa + lev * ca
            ax.plot([x0s / pts_x, x1s / pts_x],
                    [y0s / pts_y, y1s / pts_y], **kw)


def _draw_speckle(ax, x, y, width_pts: float, density_pts: float,
                  outward: bool, **kwargs) -> None:
    """Scatter dot markers near the polygon boundary."""
    pts_x, pts_y = _get_pts_per_data(ax)

    xs = x * pts_x
    ys = y * pts_y

    ds = np.sqrt(np.diff(xs) ** 2 + np.diff(ys) ** 2)
    cumds = np.concatenate([[0.0], np.cumsum(ds)])
    perimeter = float(cumds[-1])
    if perimeter < 1.0:
        return

    n_dots = max(1, int(perimeter / max(density_pts, 0.1)))
    rng = np.random.RandomState(42)
    t_vals = rng.uniform(0.0, perimeter, n_dots)

    dot_xs: list[float] = []
    dot_ys: list[float] = []
    for t in t_vals:
        idx = int(np.clip(np.searchsorted(cumds, t, side='right') - 1,
                          0, len(ds) - 1))
        seg_t = (t - cumds[idx]) / ds[idx] if ds[idx] > 1e-10 else 0.0
        px = xs[idx] + seg_t * (xs[idx + 1] - xs[idx])
        py = ys[idx] + seg_t * (ys[idx + 1] - ys[idx])

        dx = xs[idx + 1] - xs[idx]
        dy = ys[idx + 1] - ys[idx]
        length = float(np.hypot(dx, dy))
        if length > 1e-10:
            nx, ny = -dy / length, dx / length
        else:
            nx, ny = 0.0, 1.0

        sign = 1.0 if outward else -1.0
        offset = float(rng.uniform(0.0, width_pts)) * sign
        dot_xs.append(px + offset * nx)
        dot_ys.append(py + offset * ny)

    dot_xd = np.array(dot_xs) / pts_x
    dot_yd = np.array(dot_ys) / pts_y

    state = get_state()
    if state.proj is not None:
        x_min, x_max = state.x_limits
        y_min, y_max = state.y_limits
        mask = ((dot_xd >= x_min) & (dot_xd <= x_max) &
                (dot_yd >= y_min) & (dot_yd <= y_max))
        dot_xd = dot_xd[mask]
        dot_yd = dot_yd[mask]

    kw: dict = {'linestyle': 'none', 'marker': '.', 'markersize': 1}
    kw.update(kwargs)
    ax.plot(dot_xd, dot_yd, **kw)
