"""
Map decorations: scale bar (m_ruler), UTM grid (m_utmgrid).
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from .projection import m_xy2ll
from ._state import get_state

_NICE_KM = [
    0.1, 0.2, 0.5, 1, 2, 4, 5, 10, 20, 25, 50, 100, 150,
    200, 250, 500, 1000, 2000, 2500, 5000, 10000,
]
_NICE_NM = [
    0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 25, 50, 100, 150,
    200, 250, 500, 1000, 2000, 5000,
]


def _geodesic_dist_km(lon0, lat0, lon1, lat1) -> float:
    import pyproj
    geod = pyproj.Geod(ellps='sphere')
    _, _, dist_m = geod.inv(lon0, lat0, lon1, lat1)
    return abs(dist_m) / 1000.0


def _nice_dist(dist_km: float, units: str) -> float:
    table = _NICE_NM if units == 'nm' else _NICE_KM
    chosen = table[0]
    for d in table:
        if d <= dist_km:
            chosen = d
        else:
            break
    return chosen


def m_ruler(xpos, ypos, *, nbar: int = 4, units: str = 'km', **kwargs) -> None:
    """
    Draw a geographic scale bar on the current map.

    Parameters
    ----------
    xpos : array-like [x0, x1]
        Left and right edges of the bar as fractions of map width [0, 1].
    ypos : float
        Vertical centre of the bar as fraction of map height [0, 1].
    nbar : int
        Number of equal divisions (tick marks at each boundary, default 4).
    units : {'km', 'nm'}
        Distance units ('km' default, 'nm' for nautical miles).
    **kwargs
        Forwarded to ``ax.text()`` for the distance labels (e.g. fontsize).
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    ax = plt.gca()
    x_min, x_max = state.x_limits
    y_min, y_max = state.y_limits
    x_span = x_max - x_min
    y_span = y_max - y_min

    x0 = x_min + float(xpos[0]) * x_span
    x1 = x_min + float(xpos[1]) * x_span
    y_c = y_min + float(ypos) * y_span

    lon0, lat0 = m_xy2ll(x0, y_c)
    lon1, lat1 = m_xy2ll(x1, y_c)
    full_km = _geodesic_dist_km(lon0, lat0, lon1, lat1)
    if units == 'nm':
        full_dist = full_km / 1.852
    else:
        full_dist = full_km

    nice = _nice_dist(full_dist, units)
    if nice <= 0 or full_dist <= 0:
        return

    scale = nice / full_dist
    x1_actual = x0 + scale * (x1 - x0)

    bar_h = y_span * 0.012
    dx = (x1_actual - x0) / nbar

    # Alternating black/white segments
    for i in range(nbar):
        xi = x0 + i * dx
        color = 'k' if i % 2 == 0 else 'white'
        seg = mpatches.Rectangle(
            (xi, y_c - bar_h / 2), dx, bar_h,
            facecolor=color, edgecolor='k', linewidth=0.5,
            zorder=10, clip_on=False,
        )
        ax.add_patch(seg)

    # Labels
    tkw = dict(kwargs)
    tkw.setdefault('ha', 'center')
    tkw.setdefault('va', 'top')
    tkw['zorder'] = 10
    tkw['clip_on'] = False
    label_y = y_c - bar_h / 2 - bar_h * 0.6

    ax.text(x0, label_y, '0', **tkw)
    # Midpoint label
    mid_x = x0 + 0.5 * (x1_actual - x0)
    mid_dist = nice / 2
    if mid_dist >= 1 and mid_dist == int(mid_dist):
        mid_str = str(int(mid_dist))
    else:
        mid_str = f'{mid_dist:g}'
    ax.text(mid_x, label_y, mid_str, **tkw)
    # End label with units
    if nice >= 1 and nice == int(nice):
        dist_str = str(int(nice))
    else:
        dist_str = f'{nice:g}'
    ax.text(x1_actual, label_y, f'{dist_str} {units}', **tkw)


def m_utmgrid(*, box: str = 'fancy', tickdir: str = 'in', fontsize=None,
              linestyle: str = '-', linewidth: float = 0.5, grid: str = 'on',
              xaxislocation: str = 'bottom', yaxislocation: str = 'left',
              color: str = 'k', **kwargs) -> None:
    """
    Draw UTM-formatted grid/frame on a UTM-projected map.

    Tick labels use the UTM convention: 2-digit km within the 100 km band,
    with the last (largest) tick showing the full ``BAND KM METERS E/N`` label.

    Parameters
    ----------
    box : {'fancy', 'plain', 'none'}
    tickdir : {'in', 'out'}
    fontsize : float, optional
    linestyle : str
    linewidth : float
    grid : {'on', 'off'}
    xaxislocation : {'bottom', 'top'}
    yaxislocation : {'left', 'right'}
    """
    from .grid import _draw_fancy_box, _draw_simple_box

    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    ax = plt.gca()
    fs = fontsize if fontsize is not None else plt.rcParams.get('font.size', 8)

    x0, x1 = state.x_limits
    y0, y1 = state.y_limits
    x_span = x1 - x0
    y_span = y1 - y0

    # Pick a nice tick step in metres targeting ~4–8 ticks per axis
    _NICE_M = [1e3, 2e3, 5e3, 1e4, 2e4, 2.5e4, 5e4, 1e5, 2e5, 2.5e5, 5e5]
    span_m = max(x_span, y_span)
    step = _NICE_M[0]
    for s in _NICE_M:
        if span_m / s <= 8:
            step = s
            break

    x_ticks_m = np.arange(np.ceil(x0 / step) * step, x1 + step * 0.01, step)
    x_ticks_m = x_ticks_m[(x_ticks_m >= x0) & (x_ticks_m <= x1)]
    y_ticks_m = np.arange(np.ceil(y0 / step) * step, y1 + step * 0.01, step)
    y_ticks_m = y_ticks_m[(y_ticks_m >= y0) & (y_ticks_m <= y1)]

    def _utm_label(val_m: float, axis: str) -> str:
        """Short 2-digit km label; last tick gets full band label."""
        km_total = int(round(val_m / 1000))
        band = km_total // 100
        km = km_total % 100
        meters = int(round(val_m)) % 1000
        suffix = 'E' if axis == 'x' else 'N'
        return f'{band:d}{km:02d}{meters:03d} {suffix}'

    def _short_label(val_m: float) -> str:
        km_total = int(round(val_m / 1000))
        km = km_total % 100
        return f'{km:02d}'

    # Draw grid lines
    if grid == 'on':
        for xv in x_ticks_m:
            ax.plot([xv, xv], [y0, y1], color=color, linewidth=linewidth,
                    linestyle=linestyle, zorder=2, clip_on=True)
        for yv in y_ticks_m:
            ax.plot([x0, x1], [yv, yv], color=color, linewidth=linewidth,
                    linestyle=linestyle, zorder=2, clip_on=True)

    # Box
    bw = min(x_span, y_span) * 0.012
    if box == 'fancy':
        _draw_fancy_box(ax, x0, x1, y0, y1, x_ticks_m, y_ticks_m, bw)
    elif box in ('plain', 'on'):
        _draw_simple_box(ax, x0, x1, y0, y1, linewidth=linewidth)

    # Tick marks and labels
    tick_len = min(x_span, y_span) * 0.015
    pad = tick_len * 1.5

    # X-axis ticks (easting)
    x_last = x_ticks_m[-1] if len(x_ticks_m) > 0 else None
    for xv in x_ticks_m:
        label = _utm_label(xv, 'x') if xv == x_last else _short_label(xv)
        if xaxislocation == 'bottom':
            if tickdir == 'in':
                ax.plot([xv, xv], [y0, y0 + tick_len], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            else:
                ax.plot([xv, xv], [y0 - tick_len, y0], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            ax.text(xv, y0 - pad - (bw if box == 'fancy' else 0),
                    label, ha='center', va='top', fontsize=fs,
                    rotation=90 if xv == x_last else 0,
                    zorder=10, clip_on=False)
        else:
            if tickdir == 'in':
                ax.plot([xv, xv], [y1 - tick_len, y1], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            else:
                ax.plot([xv, xv], [y1, y1 + tick_len], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            ax.text(xv, y1 + pad + (bw if box == 'fancy' else 0),
                    label, ha='center', va='bottom', fontsize=fs,
                    rotation=90 if xv == x_last else 0,
                    zorder=10, clip_on=False)

    # Y-axis ticks (northing)
    y_last = y_ticks_m[-1] if len(y_ticks_m) > 0 else None
    for yv in y_ticks_m:
        label = _utm_label(yv, 'y') if yv == y_last else _short_label(yv)
        if yaxislocation == 'left':
            if tickdir == 'in':
                ax.plot([x0, x0 + tick_len], [yv, yv], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            else:
                ax.plot([x0 - tick_len, x0], [yv, yv], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            ax.text(x0 - pad - (bw if box == 'fancy' else 0),
                    yv, label, ha='right', va='center', fontsize=fs,
                    zorder=10, clip_on=False)
        else:
            if tickdir == 'in':
                ax.plot([x1 - tick_len, x1], [yv, yv], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            else:
                ax.plot([x1, x1 + tick_len], [yv, yv], color='k',
                        linewidth=0.7, zorder=10, clip_on=False)
            ax.text(x1 + pad + (bw if box == 'fancy' else 0),
                    yv, label, ha='left', va='center', fontsize=fs,
                    zorder=10, clip_on=False)

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.axis('off')
