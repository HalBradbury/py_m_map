"""
Track line with time/date annotations: m_track.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def _to_minutes(navtimes) -> np.ndarray:
    """Convert navtimes (datetime list or numeric) to minutes from first point."""
    try:
        from datetime import datetime
        if hasattr(navtimes[0], 'timestamp'):
            t0 = navtimes[0].timestamp()
            return np.array([(t.timestamp() - t0) / 60.0 for t in navtimes])
    except (IndexError, AttributeError):
        pass
    arr = np.asarray(navtimes, dtype=float)
    return (arr - arr[0]) * 24 * 60  # assume datenum (days) → minutes


def m_track(lon, lat, navtimes=None, *, ticks=60, times=240, dates=720,
            timefmt='%H:%M', datefmt='%m/%d/%y', color='k', linewidth=None,
            linestyle='-', clip='on', orient='true', fontsize=None, **kwargs) -> None:
    """
    Draw a ship track with optional tick marks and time/date annotations.

    Parameters
    ----------
    lon, lat : array-like
        Track positions in decimal degrees.
    navtimes : list of datetime or array of datenums, optional
        Time at each position. If None, positions are equally spaced in time.
    ticks : int
        Tick interval in minutes (0 = tick at every point).
    times : int
        Time-label interval in minutes (0 = no time labels).
    dates : int
        Date-label interval in minutes (0 = no date labels).
    timefmt : str
        strftime format for time labels.
    datefmt : str
        strftime format for date labels.
    color : color spec
        Line and annotation colour.
    orient : {'true', 'upright'}
        'true'   — labels follow track heading.
        'upright' — labels flipped if they would be upside-down.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    n = len(lon)

    # Project track
    x, y = m_ll2xy(lon, lat, clip=clip)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    ax = plt.gca()
    lw = linewidth if linewidth is not None else plt.rcParams.get('lines.linewidth', 1.5)
    fs = fontsize if fontsize is not None else plt.rcParams.get('font.size', 8)

    # Draw track line (zorder > 10 to render above fancy box border)
    ax.plot(x, y, color=color, linewidth=lw, linestyle=linestyle,
            zorder=11, clip_on=(clip == 'on'))

    if navtimes is None or n < 2:
        return

    t_min = _to_minutes(navtimes)
    t_span = t_min[-1] - t_min[0]
    if t_span <= 0:
        return

    x_span = state.x_limits[1] - state.x_limits[0]
    y_span = state.y_limits[1] - state.y_limits[0]
    tick_len = min(x_span, y_span) * 0.015

    def _heading_at(idx: int) -> float:
        """Heading angle in degrees at point idx (atan2 of projected dx, dy)."""
        if idx == 0:
            i0, i1 = 0, min(1, n - 1)
        elif idx == n - 1:
            i0, i1 = max(0, n - 2), n - 1
        else:
            i0, i1 = idx - 1, idx + 1
        dx = x[i1] - x[i0]
        dy = y[i1] - y[i0]
        return np.degrees(np.arctan2(dy, dx))

    def _interp_position(t_target: float):
        """Interpolate (x, y) at time t_target minutes."""
        idx = np.searchsorted(t_min, t_target)
        idx = np.clip(idx, 1, n - 1)
        t0, t1 = t_min[idx - 1], t_min[idx]
        frac = (t_target - t0) / (t1 - t0) if t1 > t0 else 0.0
        xi = x[idx - 1] + frac * (x[idx] - x[idx - 1])
        yi = y[idx - 1] + frac * (y[idx] - y[idx - 1])
        dxi = x[idx] - x[idx - 1]
        dyi = y[idx] - y[idx - 1]
        heading = np.degrees(np.arctan2(dyi, dxi))
        return xi, yi, heading

    def _draw_tick(xi, yi, heading):
        angle = heading - 90.0  # perpendicular, starboard side
        r = np.radians(angle)
        dx_t = tick_len * np.cos(r)
        dy_t = tick_len * np.sin(r)
        ax.plot([xi, xi + dx_t], [yi, yi + dy_t],
                color=color, linewidth=lw * 0.7, zorder=12, clip_on=False)

    def _draw_label(xi, yi, heading, text, side='time'):
        angle = heading - 90.0
        if orient == 'upright' and abs(angle) > 90:
            if side == 'time':
                rot = angle + 180
                ha = 'right'
            else:
                rot = angle - 180
                ha = 'left'
        else:
            rot = angle
            ha = 'left' if side == 'time' else 'right'

        offset_r = np.radians(heading - 90)
        offset_scale = tick_len * 1.2
        ox = offset_scale * np.cos(offset_r) if side == 'time' else -offset_scale * np.cos(offset_r)
        oy = offset_scale * np.sin(offset_r) if side == 'time' else -offset_scale * np.sin(offset_r)

        ax.text(xi + ox, yi + oy, text,
                color=color, fontsize=fs, rotation=rot,
                ha=ha, va='center', zorder=13, clip_on=False)

    # Determine tick/label times
    if ticks == 0:
        tick_times = list(t_min)
    else:
        t_start = np.ceil(t_min[0] / ticks) * ticks
        tick_times = list(np.arange(t_start, t_min[-1] + 1e-9, ticks))

    if times > 0:
        t_start_times = np.ceil(t_min[0] / times) * times
        label_times = set(np.arange(t_start_times, t_min[-1] + 1e-9, times))
    else:
        label_times = set()

    if dates > 0:
        t_start_dates = np.ceil(t_min[0] / dates) * dates
        date_times = set(np.arange(t_start_dates, t_min[-1] + 1e-9, dates))
    else:
        date_times = set()

    # Convert time offsets back to datetime for labelling
    try:
        base_dt = navtimes[0]
        has_datetime = hasattr(base_dt, 'strftime')
    except Exception:
        has_datetime = False

    def _fmt_time(t_minutes):
        if not has_datetime:
            return f'{int(t_minutes // 60):02d}:{int(t_minutes % 60):02d}'
        from datetime import timedelta
        dt = base_dt + timedelta(minutes=float(t_minutes))
        return dt.strftime(timefmt)

    def _fmt_date(t_minutes):
        if not has_datetime:
            return ''
        from datetime import timedelta
        dt = base_dt + timedelta(minutes=float(t_minutes))
        return dt.strftime(datefmt)

    for tt in tick_times:
        if tt < t_min[0] or tt > t_min[-1]:
            continue
        xi, yi, heading = _interp_position(tt)
        if not (np.isfinite(xi) and np.isfinite(yi)):
            continue
        _draw_tick(xi, yi, heading)

        if any(abs(tt - lt) < 1e-6 for lt in label_times):
            _draw_label(xi, yi, heading, _fmt_time(tt), side='time')

        if any(abs(tt - dt) < 1e-6 for dt in date_times):
            _draw_label(xi, yi, heading, _fmt_date(tt), side='date')
