"""
Map grid, frame, and axis tick labels.

m_grid — ported from m_grid.m
"""
from __future__ import annotations
import warnings
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, PathPatch, Polygon as MplPolygon
from matplotlib.path import Path as MplPath
from matplotlib.transforms import ScaledTranslation
from .projection import m_ll2xy
from ._state import get_state


# ---------------------------------------------------------------------------
# Tick helpers
# ---------------------------------------------------------------------------

_NICE_STEPS = [
    0.05, 0.1, 0.25, 0.5,
    1, 2, 5, 10, 15, 20, 25, 30, 45, 60, 90,
]


def _nice_ticks(lo: float, hi: float, target: int = 4) -> np.ndarray:
    """
    Return evenly-spaced 'nice' tick values spanning [lo, hi].

    Picks the step from _NICE_STEPS that gives a tick count closest to
    `target`.  Using target=4 by default avoids label crowding on small
    regional maps.
    """
    span = hi - lo
    if span == 0:
        return np.array([lo])
    step = min(_NICE_STEPS, key=lambda s: abs(span / s - target))
    start = np.ceil(lo / step) * step
    stop = np.floor(hi / step) * step
    ticks = np.arange(start, stop + step * 1e-6, step)
    return ticks[(ticks >= lo - 1e-9) & (ticks <= hi + 1e-9)]


def _fmt_lat(deg: float) -> str:
    """Format latitude: e.g.  48°46'N  or  49°N"""
    hemi = 'N' if deg >= 0 else 'S'
    d = abs(deg)
    whole = int(d)
    mins = round((d - whole) * 60)
    if mins == 60:
        whole += 1
        mins = 0
    if mins == 0:
        return f"{whole}\N{DEGREE SIGN}{hemi}"
    return f"{whole}\N{DEGREE SIGN}{mins:02d}'{hemi}"


def _fmt_lon(deg: float) -> str:
    """Format longitude: e.g.  125°15'W  or  124°E"""
    hemi = 'E' if deg >= 0 else 'W'
    d = abs(deg)
    whole = int(d)
    mins = round((d - whole) * 60)
    if mins == 60:
        whole += 1
        mins = 0
    if mins == 0:
        return f"{whole}\N{DEGREE SIGN}{hemi}"
    return f"{whole}\N{DEGREE SIGN}{mins:02d}'{hemi}"


def _labels_enabled(param) -> bool:
    """Return True if tick labels should be drawn."""
    if param is None:
        return True
    if param is False:
        return False
    if isinstance(param, (list, np.ndarray)) and len(param) == 0:
        return False
    return True


def _warn_unsupported_label_options(xticklabels, yticklabels, xlabeldir) -> None:
    """
    Warn about m_grid options that are accepted but not acted on.

    Both are documented in a way that invites more than they deliver, and
    silently ignoring them is worse than saying so: a caller who passes custom
    label text gets the auto-formatted labels and no indication why.
    """
    for name, param in (('xticklabels', xticklabels), ('yticklabels', yticklabels)):
        # A non-empty sequence of label *text* — as opposed to None/True/False or
        # [] , which are the supported on/off forms.
        if isinstance(param, (list, tuple, np.ndarray)) and len(param) > 0:
            warnings.warn(
                f"m_grid: {name} controls only whether labels are drawn; the "
                f"supplied label text is ignored and auto-formatted degree "
                f"labels are used instead. Pass False or [] to suppress labels. "
                f"Use the returned axes to relabel manually if you need custom "
                f"text.",
                UserWarning, stacklevel=3,
            )
    if xlabeldir is not None and str(xlabeldir) != 'mid':
        warnings.warn(
            f"m_grid: xlabeldir={xlabeldir!r} is not implemented and has no "
            f"effect; longitude labels are always drawn in the 'mid' "
            f"orientation.",
            UserWarning, stacklevel=3,
        )


# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def m_grid(
    *,
    box: str = 'on',
    grid: str = 'on',
    tickdir: str = 'in',
    fontsize: float | None = None,
    lon_ticks: np.ndarray | None = None,
    lat_ticks: np.ndarray | None = None,
    xtick=None,
    ytick=None,
    xticklabels=None,
    yticklabels=None,
    linestyle: str = '-',
    linest: str | None = None,
    lat_label_lon: float | None = None,
    color=None,
    yaxislocation: str = 'left',
    xaxislocation: str = 'bottom',
    xlabeldir: str = 'mid',
    ticklen: float = 0.0,
    linewidth: float = 1.0,
    gridcolor=None,
    backcolor=None,
    boxstyle: str = 'fill',
) -> None:
    """
    Draw a lat/lon grid and frame on the current map axes.

    Parameters
    ----------
    box : {'on', 'off', 'fancy'}
        'fancy' draws the distinctive alternating black/white border.
        For circular projections (e.g. orthographic) a circle is drawn instead.
    boxstyle : {'fill', 'line'}
        Only used when box='fancy'.  'fill' (default) draws solid alternating
        black/white patches.  'line' draws a centre line along each edge with
        perpendicular tick marks at each lat/lon tick position — a clean ruler
        style with no filled patches.
    grid : {'on', 'off', 'none'}
        Whether to draw lat/lon grid lines inside the map.
    tickdir : {'in', 'out'}
        Direction of tick marks on the fancy box (rectangular only).
    fontsize : float or None
        Font size for tick labels.  None uses the axes default.
    lon_ticks, lat_ticks : array-like or None
        Explicit tick positions in decimal degrees.  Auto-computed if None.
        Overridden by xtick / ytick when those are provided.
    xtick : scalar or array-like, optional
        If scalar: longitude tick step in degrees (e.g. xtick=12 → every 12°).
        If array: explicit longitude tick positions.
    ytick : scalar or array-like, optional
        If scalar: latitude tick step in degrees.
        If array: explicit latitude tick positions (e.g. ytick=[70, 80]).
    xticklabels : None, False, or []
        None/True → show longitude labels (default).
        False or [] → suppress longitude labels.
        On/off only: custom label *text* is not supported, and passing a
        non-empty list warns and falls back to auto-formatted degree labels.
    yticklabels : None, False, or []
        None/True → show latitude labels (default).
        False or [] → suppress latitude labels.
        On/off only, as for xticklabels.
    linestyle : str
        Line style for grid lines (default '-').
    linest : str or None
        MATLAB-compatible alias for linestyle.
    lat_label_lon : float or None
        Longitude (degrees) of the meridian along which latitude labels are
        placed on circular maps (orthographic, stereographic, azimuthal).
        None (default) instead places each label at its parallel's left-most
        point on the map boundary.  On a polar map that point lies on the
        meridian 90° from the projection centre, so the latitude labels land on
        top of that meridian's own label — pass an explicit value between two
        longitude ticks to separate them (see REVIEW.md M11).
    color : str, tuple, or None
        Colour for grid lines.  None defaults to 'k' for most projections.
        MATLAB-compatible (e.g. color='k' or color=[.7 .7 .7]).
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    _warn_unsupported_label_options(xticklabels, yticklabels, xlabeldir)

    # MATLAB-style aliases
    if linest is not None:
        linestyle = linest
    if gridcolor is not None and color is None:
        color = gridcolor

    # xtick / ytick → override lon_ticks / lat_ticks
    if xtick is not None:
        xt = np.atleast_1d(np.asarray(xtick, dtype=float))
        if xt.size == 1:
            step = float(xt[0])
            if state.projection_type == 'circular':
                # Full 360° of longitude for circular (polar/global) maps
                lon_ticks = np.arange(-180.0, 180.0, step)
            else:
                lo, hi = state.lon_limits
                start = np.ceil(lo / step) * step
                lon_ticks = np.arange(start, hi + step * 1e-6, step)
        else:
            lon_ticks = xt

    if ytick is not None:
        yt = np.atleast_1d(np.asarray(ytick, dtype=float))
        if yt.size == 1:
            step = float(yt[0])
            lo, hi = state.lat_limits
            start = np.ceil(lo / step) * step
            lat_ticks = np.arange(start, hi + step * 1e-6, step)
        else:
            lat_ticks = yt

    ax = plt.gca()

    grid_color = color if color is not None else 'k'

    if state.projection_type == 'circular':
        _draw_grid_circular(
            ax, state, box, grid,
            lon_ticks, lat_ticks,
            xticklabels, yticklabels,
            linestyle, fontsize,
            lat_label_lon=lat_label_lon,
            grid_color=grid_color,
        )
    elif state.projection_type == 'conic':
        _draw_grid_conic(
            ax, state, box, grid, tickdir,
            lon_ticks, lat_ticks,
            xticklabels, yticklabels,
            linestyle, fontsize,
            linewidth=linewidth,
            boxstyle=boxstyle,
        )
    elif state.projection_type == 'pseudocylindrical':
        _draw_grid_pseudocylindrical(
            ax, state, box, grid,
            lon_ticks, lat_ticks,
            xticklabels, yticklabels,
            linestyle, fontsize,
            grid_color,
            backcolor=backcolor,
            xaxislocation=xaxislocation,
        )
        # For full-world projections set explicit limits so the oval is centered;
        # for interrupted lobes leave autoscaling to accumulate all lobes.
        lon_min_s, lon_max_s = state.lon_limits
        if (lon_max_s - lon_min_s) >= 359.9:
            ax.set_xlim(state.x_limits)
            ax.set_ylim(state.y_limits)
        else:
            ax.relim()
            ax.autoscale_view()
            ax.margins(0)
    elif state.projection_type == 'oblique':
        _draw_grid_oblique(
            ax, state, box, grid, tickdir,
            lon_ticks, lat_ticks,
            xticklabels, yticklabels,
            linestyle, fontsize,
            yaxislocation=yaxislocation,
            xaxislocation=xaxislocation,
            ticklen=ticklen,
        )
    else:
        _draw_grid_rectangular(
            ax, state, box, grid, tickdir,
            lon_ticks, lat_ticks,
            xticklabels, yticklabels,
            linestyle, fontsize,
            linewidth=linewidth,
            grid_color=grid_color,
            backcolor=backcolor,
            boxstyle=boxstyle,
            xaxislocation=xaxislocation,
            yaxislocation=yaxislocation,
        )


# ---------------------------------------------------------------------------
# Conic grid (Lambert Conformal Conic, etc.)
# ---------------------------------------------------------------------------

def _draw_grid_conic(
    ax, state, box, grid, tickdir,
    lon_ticks, lat_ticks,
    xticklabels, yticklabels,
    linestyle, fontsize,
    linewidth: float = 1.0,
    boxstyle: str = 'fill',
):
    x0, x1 = state.x_limits
    y0, y1 = state.y_limits

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_axis_off()

    if lon_ticks is None:
        lon_ticks = _nice_ticks(state.lon_limits[0], state.lon_limits[1], target=5)
    if lat_ticks is None:
        lat_ticks = _nice_ticks(state.lat_limits[0], state.lat_limits[1], target=5)

    lon_ticks = np.asarray(lon_ticks, dtype=float)
    lat_ticks = np.asarray(lat_ticks, dtype=float)

    # Only keep ticks strictly inside the extent (boundary ticks are the frame)
    lon_inner = lon_ticks[
        (lon_ticks > state.lon_limits[0]) & (lon_ticks < state.lon_limits[1])
    ]
    lat_inner = lat_ticks[
        (lat_ticks > state.lat_limits[0]) & (lat_ticks < state.lat_limits[1])
    ]

    span = min(x1 - x0, y1 - y0)
    bw = span * 0.013  # border width

    # ------------------------------------------------------------------
    # Grid lines (curved meridians and parallels)
    # ------------------------------------------------------------------
    if grid not in ('none', 'off', 'no'):
        n_pts = 150

        lat_pts = np.linspace(state.lat_limits[0], state.lat_limits[1], n_pts)
        for lon_v in lon_inner:
            x, y = m_ll2xy(np.full(n_pts, lon_v), lat_pts, clip='on')
            ax.plot(x, y, color='k', linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

        lon_pts = np.linspace(state.lon_limits[0], state.lon_limits[1], n_pts * 2)
        for lat_v in lat_inner:
            x, y = m_ll2xy(lon_pts, np.full(n_pts * 2, lat_v), clip='on')
            ax.plot(x, y, color='k', linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

    # ------------------------------------------------------------------
    # Boundary frame / fancy box
    # ------------------------------------------------------------------
    lon_min, lon_max = state.lon_limits
    lat_min, lat_max = state.lat_limits
    n_edge = 300

    # The 4 boundary edges in map coordinates.
    # Ordering: bottom left→right, top right→left, right bottom→top, left top→bottom.
    lons_b = np.linspace(lon_min, lon_max, n_edge)
    lons_t = np.linspace(lon_max, lon_min, n_edge)
    lats_r = np.linspace(lat_min, lat_max, n_edge)
    lats_l = np.linspace(lat_max, lat_min, n_edge)

    x_b, y_b = m_ll2xy(lons_b, np.full(n_edge, lat_min), clip='off')
    x_t, y_t = m_ll2xy(lons_t, np.full(n_edge, lat_max), clip='off')
    x_r, y_r = m_ll2xy(np.full(n_edge, lon_max), lats_r, clip='off')
    x_l, y_l = m_ll2xy(np.full(n_edge, lon_min), lats_l, clip='off')

    # Map centre used in outward-normal computation
    x_cen = (x0 + x1) / 2.0
    y_cen = (y0 + y1) / 2.0

    # Pre-compute outward normals for all edges — needed for box strips, corners,
    # and tick-label rotation regardless of box style.
    nx_b, ny_b = _edge_outward_normals(x_b, y_b, x_cen, y_cen)
    nx_r, ny_r = _edge_outward_normals(x_r, y_r, x_cen, y_cen)
    nx_t, ny_t = _edge_outward_normals(x_t, y_t, x_cen, y_cen)
    nx_l, ny_l = _edge_outward_normals(x_l, y_l, x_cen, y_cen)

    if box == 'fancy':
        lw = 0.4
        _conic_fancy_edge(ax, x_b, y_b, nx_b, ny_b, lons_b, lon_inner, bw, lw, style=boxstyle)
        _conic_fancy_edge(ax, x_r, y_r, nx_r, ny_r, lats_r, lat_inner, bw, lw, style=boxstyle)
        _conic_fancy_edge(ax, x_t, y_t, nx_t, ny_t, lons_t, lon_inner, bw, lw, style=boxstyle)
        _conic_fancy_edge(ax, x_l, y_l, nx_l, ny_l, lats_l, lat_inner, bw, lw, style=boxstyle)

        # Corners: parallelogram patch at each corner using the outward normals of
        # the two adjacent edges.  For conformal projections (Lambert conic) the
        # normals are perpendicular at every corner, so the parallelogram is an
        # exact square aligned with the local frame geometry.
        #
        # corner_normals: (cx, cy, n1x, n1y, n2x, n2y)
        #   n1 = normal of the edge whose START is at this corner
        #   n2 = normal of the edge whose END   is at this corner
        #   (edge ordering: bottom L→R, right B→T, top R→L, left T→B)
        #
        # Strip colour at each corner:
        #   bottom start (BL) = k,     bottom end (BR) = white
        #   right  start (BR) = k,     right  end (TR) = white
        #   top    start (TR) = k,     top    end (TL) = white
        #   left   start (TL) = k,     left   end (BL) = white
        corner_normals = [
            (x_b[0],  y_b[0],  nx_b[0],  ny_b[0],  nx_l[-1], ny_l[-1]),  # BL
            (x_b[-1], y_b[-1], nx_b[-1], ny_b[-1], nx_r[0],  ny_r[0]),   # BR
            (x_r[-1], y_r[-1], nx_r[-1], ny_r[-1], nx_t[0],  ny_t[0]),   # TR
            (x_t[-1], y_t[-1], nx_t[-1], ny_t[-1], nx_l[0],  ny_l[0]),   # TL
        ]
        # fill colours for the two triangles: (c1 for n1 side, c2 for n2 side)
        corner_colors = [
            ('k',     'white'),  # BL: bottom-start=k,  left-end=white
            ('white', 'k'),      # BR: bottom-end=white, right-start=k
            ('white', 'k'),      # TR: right-end=white,  top-start=k
            ('white', 'k'),      # TL: top-end=white,    left-start=k
        ]

        if boxstyle == 'line':
            for (cx, cy, n1x, n1y, n2x, n2y) in corner_normals:
                ox = cx + bw * (n1x + n2x)
                oy = cy + bw * (n1y + n2y)
                ax.fill([cx, cx + bw*n1x, ox, cx + bw*n2x],
                        [cy, cy + bw*n1y, oy, cy + bw*n2y],
                        fc='white', ec='none', clip_on=False, zorder=13)
                ax.plot([cx, ox], [cy, oy],
                        'k-', linewidth=lw, antialiased=True,
                        solid_capstyle='butt', clip_on=False, zorder=14)
                ax.plot([cx + bw*n1x, ox, cx + bw*n2x],
                        [cy + bw*n1y, oy, cy + bw*n2y],
                        'k-', linewidth=lw, antialiased=True,
                        solid_capstyle='butt', clip_on=False, zorder=14)
        else:
            for (cx, cy, n1x, n1y, n2x, n2y), (c1, c2) in zip(corner_normals, corner_colors):
                ox = cx + bw * (n1x + n2x)
                oy = cy + bw * (n1y + n2y)
                ax.fill([cx, cx + bw*n1x, ox],
                        [cy, cy + bw*n1y, oy],
                        fc=c1, ec='k', linewidth=lw,
                        clip_on=False, zorder=13)
                ax.fill([cx, ox, cx + bw*n2x],
                        [cy, oy, cy + bw*n2y],
                        fc=c2, ec='k', linewidth=lw,
                        clip_on=False, zorder=13)

    elif box in ('on', 'yes'):
        x_bnd = np.concatenate([x_b, x_r, x_t, x_l, [x_b[0]]])
        y_bnd = np.concatenate([y_b, y_r, y_t, y_l, [y_b[0]]])
        ax.plot(x_bnd, y_bnd, 'k-', linewidth=linewidth, clip_on=False, zorder=10)
    # else box='off' → nothing

    # Inner boundary line so data is visually contained
    if box in ('on', 'fancy', 'yes'):
        x_bnd = np.concatenate([x_b, x_r, x_t, x_l, [x_b[0]]])
        y_bnd = np.concatenate([y_b, y_r, y_t, y_l, [y_b[0]]])
        ax.plot(x_bnd, y_bnd, 'k-', linewidth=0.5, clip_on=False, zorder=11)

    # ------------------------------------------------------------------
    # White outer mask — covers areas outside the curved conic frame
    # (the Lambert conic top boundary curves, leaving triangular corners
    # between the curved frame and the rectangular axes extent).
    # ------------------------------------------------------------------
    frame_x = np.concatenate([x_b, x_r, x_t, x_l])
    frame_y = np.concatenate([y_b, y_r, y_t, y_l])
    n_frame = len(frame_x)

    # Outer CCW rectangle
    out_v = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]])
    out_c = [MplPath.MOVETO, MplPath.LINETO, MplPath.LINETO,
             MplPath.LINETO, MplPath.CLOSEPOLY]

    # Inner frame reversed (CW) so non-zero winding rule creates a donut
    in_fx = frame_x[::-1]
    in_fy = frame_y[::-1]
    in_v = np.column_stack([np.append(in_fx, in_fx[0]),
                             np.append(in_fy, in_fy[0])])
    in_c = ([MplPath.MOVETO] + [MplPath.LINETO] * (n_frame - 1) +
            [MplPath.CLOSEPOLY])

    mask_verts = np.vstack([out_v, in_v])
    mask_codes = np.array(out_c + in_c, dtype=np.uint8)
    ax.add_patch(PathPatch(
        MplPath(mask_verts, mask_codes),
        facecolor='white', edgecolor='none', zorder=9, clip_on=False,
    ))

    # ------------------------------------------------------------------
    # Outward tick marks (tickdir='out', box='on' only)
    # For the fancy box the strip pattern already provides visual ticks.
    # ------------------------------------------------------------------
    if tickdir == 'out' and box in ('on', 'yes'):
        tick_len = bw  # tick length matches the border strip width

        # Helper: draw a single outward tick at (xi, yi) in direction (nxi, nyi)
        def _tick(xi, yi, nxi, nyi):
            ax.plot([xi, xi + tick_len * nxi], [yi, yi + tick_len * nyi],
                    'k-', linewidth=linewidth, clip_on=False, zorder=12)

        # lons_t is descending; reverse for np.interp (needs ascending xp)
        lons_t_asc = lons_t[::-1]
        x_t_asc, y_t_asc = x_t[::-1], y_t[::-1]
        nx_t_asc, ny_t_asc = nx_t[::-1], ny_t[::-1]

        # lats_l is descending; reverse for np.interp
        lats_l_asc_tick = lats_l[::-1]
        x_l_asc, y_l_asc = x_l[::-1], y_l[::-1]
        nx_l_asc, ny_l_asc = nx_l[::-1], ny_l[::-1]

        for lon_v in lon_inner:
            # Bottom edge tick
            _tick(float(np.interp(lon_v, lons_b, x_b)),
                  float(np.interp(lon_v, lons_b, y_b)),
                  float(np.interp(lon_v, lons_b, nx_b)),
                  float(np.interp(lon_v, lons_b, ny_b)))
            # Top edge tick
            _tick(float(np.interp(lon_v, lons_t_asc, x_t_asc)),
                  float(np.interp(lon_v, lons_t_asc, y_t_asc)),
                  float(np.interp(lon_v, lons_t_asc, nx_t_asc)),
                  float(np.interp(lon_v, lons_t_asc, ny_t_asc)))

        for lat_v in lat_inner:
            # Right edge tick (lats_r is ascending)
            _tick(float(np.interp(lat_v, lats_r, x_r)),
                  float(np.interp(lat_v, lats_r, y_r)),
                  float(np.interp(lat_v, lats_r, nx_r)),
                  float(np.interp(lat_v, lats_r, ny_r)))
            # Left edge tick
            _tick(float(np.interp(lat_v, lats_l_asc_tick, x_l_asc)),
                  float(np.interp(lat_v, lats_l_asc_tick, y_l_asc)),
                  float(np.interp(lat_v, lats_l_asc_tick, nx_l_asc)),
                  float(np.interp(lat_v, lats_l_asc_tick, ny_l_asc)))

    # ------------------------------------------------------------------
    # Inward tick marks (tickdir='in', box='on' only)
    # ------------------------------------------------------------------
    if tickdir == 'in' and box in ('on', 'yes'):
        tick_len = bw

        def _tick_in(xi, yi, nxi, nyi):
            ax.plot([xi, xi - tick_len * nxi], [yi, yi - tick_len * nyi],
                    'k-', linewidth=linewidth, clip_on=True, zorder=12)

        lons_t_asc_in = lons_t[::-1]
        x_t_asc_in, y_t_asc_in = x_t[::-1], y_t[::-1]
        nx_t_asc_in, ny_t_asc_in = nx_t[::-1], ny_t[::-1]

        lats_l_asc_in = lats_l[::-1]
        x_l_asc_in, y_l_asc_in = x_l[::-1], y_l[::-1]
        nx_l_asc_in, ny_l_asc_in = nx_l[::-1], ny_l[::-1]

        for lon_v in lon_inner:
            _tick_in(float(np.interp(lon_v, lons_b, x_b)),
                     float(np.interp(lon_v, lons_b, y_b)),
                     float(np.interp(lon_v, lons_b, nx_b)),
                     float(np.interp(lon_v, lons_b, ny_b)))
            _tick_in(float(np.interp(lon_v, lons_t_asc_in, x_t_asc_in)),
                     float(np.interp(lon_v, lons_t_asc_in, y_t_asc_in)),
                     float(np.interp(lon_v, lons_t_asc_in, nx_t_asc_in)),
                     float(np.interp(lon_v, lons_t_asc_in, ny_t_asc_in)))

        for lat_v in lat_inner:
            _tick_in(float(np.interp(lat_v, lats_r, x_r)),
                     float(np.interp(lat_v, lats_r, y_r)),
                     float(np.interp(lat_v, lats_r, nx_r)),
                     float(np.interp(lat_v, lats_r, ny_r)))
            _tick_in(float(np.interp(lat_v, lats_l_asc_in, x_l_asc_in)),
                     float(np.interp(lat_v, lats_l_asc_in, y_l_asc_in)),
                     float(np.interp(lat_v, lats_l_asc_in, nx_l_asc_in)),
                     float(np.interp(lat_v, lats_l_asc_in, ny_l_asc_in)))

    # ------------------------------------------------------------------
    # Tick labels
    # ------------------------------------------------------------------
    show_x = _labels_enabled(xticklabels)
    show_y = _labels_enabled(yticklabels)
    fs = fontsize
    # Label offsets in points (screen space) beyond the outer edge of the border strip.
    # Using ScaledTranslation so spacing is independent of the projection scale.
    # Anchor point is placed at the outer border strip edge (data coords: bw * normal),
    # then shifted by a small fixed point offset for visual clearance.
    tick_pts = 3.0 if tickdir == 'out' else 0.0
    lon_gap_pts = 9.0 + tick_pts   # gap from strip outer edge to lon label centre
    lat_gap_pts = 15.0 + tick_pts  # distance from strip outer edge to centre of lat label

    if show_x:
        # Longitude labels at the bottom edge.
        # Rotation follows the local edge tangent so labels curve with the border.
        for lon_v in lon_inner:
            xv, yv = m_ll2xy([lon_v], [lat_min], clip='off')
            xv, yv = float(xv[0]), float(yv[0])
            if not (np.isfinite(xv) and np.isfinite(yv)):
                continue
            nxi = float(np.interp(lon_v, lons_b, nx_b))
            nyi = float(np.interp(lon_v, lons_b, ny_b))
            # Anchor at outer edge of border strip (data coords)
            ax_x = xv + bw * nxi
            ax_y = yv + bw * nyi
            # Additional offset in points along the outward normal
            trans = ax.transData + ScaledTranslation(
                lon_gap_pts * nxi / 72.0,
                lon_gap_pts * nyi / 72.0,
                ax.figure.dpi_scale_trans,
            )
            # Tangent along the edge in the positive-longitude direction
            tx, ty = -nyi, nxi
            angle = np.degrees(np.arctan2(ty, tx))
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180
            ax.text(ax_x, ax_y, _fmt_lon(lon_v),
                    transform=trans, ha='center', va='center',
                    rotation=angle, fontsize=fs, clip_on=False, zorder=15)

    if show_y:
        # Latitude labels at the left edge.
        # Each label is placed at the midpoint between its tick and the next tick
        # so it sits centred within the black+white strip pair for that interval.
        # ha='right': right end of each label sits at the anchor → text extends outward.
        # Rotation perpendicular to the edge (along outward normal).
        # lats_l is descending (lat_max→lat_min); reverse for np.interp.
        lats_l_asc = lats_l[::-1]
        nx_l_asc   = nx_l[::-1]
        ny_l_asc   = ny_l[::-1]
        for lat_v in lat_inner:
            xv, yv = m_ll2xy([lon_min], [lat_v], clip='off')
            xv, yv = float(xv[0]), float(yv[0])
            if not (np.isfinite(xv) and np.isfinite(yv)):
                continue
            nxi = float(np.interp(lat_v, lats_l_asc, nx_l_asc))
            nyi = float(np.interp(lat_v, lats_l_asc, ny_l_asc))
            angle = np.degrees(np.arctan2(nyi, nxi))
            if angle > 90:
                angle -= 180
            elif angle < -90:
                angle += 180
            # Place anchor at the outer strip edge (both x and y components of the
            # outward normal), then shift further by lat_gap_pts along the normal.
            # ha='center', va='center': text centre at anchor → visually centred on
            # the grid line regardless of rotation. With ha='right' the anchor sits
            # at the 'N' character (bottom of the rotated text in screen-y for LCC),
            # making labels appear low; ha='center' corrects this.
            # Must use both nxi and nyi — the LCC left-edge normal has a large
            # nyi component (~0.7), so ignoring it causes ~1 text-height offset.
            ax_x = xv + bw * nxi
            ax_y = yv + bw * nyi
            # Small downward correction: va='center' reserves descender space that
            # latitude labels (e.g. "40°N") don't use, so glyphs sit slightly high.
            fs_pts = fs if fs is not None else plt.rcParams['font.size']
            descender_corr = -(fs_pts * 0.12) / 72.0
            trans = ax.transData + ScaledTranslation(
                lat_gap_pts * nxi / 72.0,
                lat_gap_pts * nyi / 72.0 + descender_corr,
                ax.figure.dpi_scale_trans,
            )
            ax.text(ax_x, ax_y, _fmt_lat(lat_v),
                    transform=trans, ha='center', va='center',
                    rotation=angle, fontsize=fs, clip_on=False, zorder=15)


def _outward_unit(x: np.ndarray, y: np.ndarray,
                  x_cen: float, y_cen: float) -> tuple[np.ndarray, np.ndarray]:
    """Unit vector pointing away from the map centre at each (x, y)."""
    dx = x - x_cen
    dy = y - y_cen
    mag = np.hypot(dx, dy)
    mag = np.where(mag < 1e-10, 1.0, mag)
    return dx / mag, dy / mag


def _edge_outward_normals(x_edge: np.ndarray, y_edge: np.ndarray,
                           x_cen: float, y_cen: float
                           ) -> tuple[np.ndarray, np.ndarray]:
    """
    Per-point outward unit normals for a curve, pointing away from the centre.

    The normal is the component of the centrifugal direction perpendicular to
    the local tangent, normalised.  This gives smooth, physically correct
    outward directions even on strongly curved edges.
    """
    # Tangent by central differences
    tx = np.gradient(x_edge)
    ty = np.gradient(y_edge)
    t_len = np.hypot(tx, ty)
    t_len = np.where(t_len < 1e-10, 1.0, t_len)
    tx, ty = tx / t_len, ty / t_len

    # Normal candidates: perpendicular to tangent
    nx, ny = -ty, tx

    # Choose the sign that points away from the map centre
    dx, dy = x_edge - x_cen, y_edge - y_cen
    dot = nx * dx + ny * dy
    if np.mean(dot) < 0:
        nx, ny = -nx, -ny

    return nx, ny


def _conic_fancy_edge(ax, x_edge, y_edge, nx, ny, param_vals, tick_vals, bw, lw, style='fill'):
    """
    Draw alternating black/white strips along one curved boundary edge.

    Parameters
    ----------
    nx, ny : pre-computed per-point outward unit normals (from _edge_outward_normals).
             Passed in so the same arrays can be reused for the corner geometry.
    style : 'fill' (default) — solid black/white alternating strips.
            'line' — ruler style: all strips white; black strips get a thin
            centre line; separator lines drawn at every break boundary.

    Break points are interpolated exactly so adjacent strips share identical
    boundary vertices and there are no gaps.
    """
    x_outer = x_edge + bw * nx
    y_outer = y_edge + bw * ny
    x_mid   = x_edge + (bw / 2.0) * nx
    y_mid   = y_edge + (bw / 2.0) * ny

    # Build segment breakpoints along the edge parameter
    p0, p1 = param_vals[0], param_vals[-1]
    ascending = p1 >= p0
    ticks_in = tick_vals[
        (tick_vals > min(p0, p1)) & (tick_vals < max(p0, p1))
    ]
    if ascending:
        breaks = np.concatenate([[p0], np.sort(ticks_in), [p1]])
    else:
        breaks = np.concatenate([[p0], np.sort(ticks_in)[::-1], [p1]])

    # Subdivide each interval at its midpoint so every grid interval contains
    # one black strip (first half) and one white strip (second half).
    sub = [breaks[0]]
    for i in range(1, len(breaks)):
        sub.append((breaks[i - 1] + breaks[i]) / 2.0)
        sub.append(breaks[i])
    breaks = np.array(sub)

    # Build interpolators using np.interp (requires ascending xp)
    pv = param_vals if ascending else param_vals[::-1]
    xi_arr = x_edge  if ascending else x_edge[::-1]
    yi_arr = y_edge  if ascending else y_edge[::-1]
    xo_arr = x_outer if ascending else x_outer[::-1]
    yo_arr = y_outer if ascending else y_outer[::-1]
    xm_arr = x_mid   if ascending else x_mid[::-1]
    ym_arr = y_mid   if ascending else y_mid[::-1]

    def _interp_pt(pval):
        """Return (x_inner, y_inner, x_outer, y_outer, x_mid, y_mid) at pval."""
        return (
            float(np.interp(pval, pv, xi_arr)),
            float(np.interp(pval, pv, yi_arr)),
            float(np.interp(pval, pv, xo_arr)),
            float(np.interp(pval, pv, yo_arr)),
            float(np.interp(pval, pv, xm_arr)),
            float(np.interp(pval, pv, ym_arr)),
        )

    for i, (pa, pb) in enumerate(zip(breaks[:-1], breaks[1:])):
        if ascending:
            mask = (param_vals >= pa) & (param_vals <= pb)
        else:
            mask = (param_vals <= pa) & (param_vals >= pb)

        # Interpolated exact endpoints guarantee zero gap between adjacent strips
        xa_i, ya_i, xa_o, ya_o, xa_m, ya_m = _interp_pt(pa)
        xb_i, yb_i, xb_o, yb_o, xb_m, yb_m = _interp_pt(pb)

        xi_seg = x_edge[mask]
        yi_seg = y_edge[mask]
        xo_seg = x_outer[mask]
        yo_seg = y_outer[mask]
        xm_seg = x_mid[mask]
        ym_seg = y_mid[mask]

        xi_full = np.concatenate([[xa_i], xi_seg, [xb_i]])
        yi_full = np.concatenate([[ya_i], yi_seg, [yb_i]])
        xo_full = np.concatenate([[xa_o], xo_seg, [xb_o]])
        yo_full = np.concatenate([[ya_o], yo_seg, [yb_o]])
        xm_full = np.concatenate([[xa_m], xm_seg, [xb_m]])
        ym_full = np.concatenate([[ya_m], ym_seg, [yb_m]])

        if len(xi_full) < 2:
            continue

        # Strip polygon: inner edge forward, outer edge reversed
        poly_x = np.concatenate([xi_full, xo_full[::-1]])
        poly_y = np.concatenate([yi_full, yo_full[::-1]])

        if style == 'line':
            ax.fill(poly_x, poly_y, fc='white', ec='none', clip_on=False, zorder=10)
            if i % 2 == 0:  # "black" strip → thin centre line
                ax.plot(xm_full, ym_full, 'k-', linewidth=lw, clip_on=False, zorder=12)
        else:
            color = 'k' if i % 2 == 0 else 'white'
            ax.fill(poly_x, poly_y, fc=color, ec='k', linewidth=lw,
                    clip_on=False, zorder=10)

    # Ruler style: separator lines at every break boundary + outer boundary line
    if style == 'line':
        for pb in breaks:
            xi, yi, xo, yo, _, _ = _interp_pt(pb)
            ax.plot([xi, xo], [yi, yo], 'k-', linewidth=lw, clip_on=False, zorder=12)
        ax.plot(x_outer, y_outer, 'k-', linewidth=lw, clip_on=False, zorder=11)


# ---------------------------------------------------------------------------
# Pseudocylindrical grid (sinusoidal, Mollweide, etc.)
# ---------------------------------------------------------------------------

def _draw_grid_pseudocylindrical(
    ax, state, box, grid,
    lon_ticks, lat_ticks,
    xticklabels, yticklabels,
    linestyle, fontsize,
    color='k',
    backcolor=None,
    xaxislocation='bottom',
):
    """
    Draw grid for a single pseudocylindrical lobe (sinusoidal, Mollweide, etc.).

    Does NOT set axis limits — the caller uses ax.relim() / autoscale_view()
    after all lobes have been drawn, as in MATLAB m_map's interrupted projections.
    """
    lon_min, lon_max = state.lon_limits
    lat_min, lat_max = state.lat_limits

    ax.set_aspect('equal')
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.patch.set_visible(False)

    if lon_ticks is None:
        lon_ticks = _nice_ticks(lon_min, lon_max, target=4)
    if lat_ticks is None:
        lat_ticks = _nice_ticks(lat_min, lat_max, target=4)

    lon_ticks = np.asarray(lon_ticks, dtype=float)
    lat_ticks = np.asarray(lat_ticks, dtype=float)

    # Projected boundary of this lobe.
    # For full-world pseudocylindrical projections (lon_max - lon_min ≈ 360°),
    # the left/right boundary meridians are at the projection cut (center ± 180°).
    # Approaching from either side gives the left vs right half of the ellipse.
    # Using the exact ±180° longitude fails when the center is not 0° because
    # both map to the *same* geographic meridian.
    # For partial lobes (interrupted projections), use lon_min/lon_max directly.
    n = 300
    full_world = (lon_max - lon_min) >= 359.9

    if full_world:
        clon = getattr(state, 'center_lon', 0.0)
        cut = clon - 180.0
        while cut > 180.0:
            cut -= 360.0
        while cut < -180.0:
            cut += 360.0
        eps = 1e-3
        left_lon = cut + eps    # east of cut → left half (negative x)
        right_lon = cut - eps   # west of cut → right half (positive x)
        if right_lon < -180.0:
            right_lon += 360.0
        if right_lon > 180.0:
            right_lon -= 360.0
    else:
        left_lon = lon_min
        right_lon = lon_max

    lons_b = np.linspace(lon_min, lon_max, n)
    lons_t = np.linspace(lon_max, lon_min, n)
    lats_l = np.linspace(lat_min, lat_max, n)
    lats_r = np.linspace(lat_max, lat_min, n)

    xb, yb = m_ll2xy(lons_b, np.full(n, lat_min), clip='off')
    xr, yr = m_ll2xy(np.full(n, right_lon), lats_l, clip='off')
    xt, yt = m_ll2xy(lons_t, np.full(n, lat_max), clip='off')
    xl, yl = m_ll2xy(np.full(n, left_lon), lats_r, clip='off')

    # Convert to arrays and filter infinite values (poles converge to a point)
    xb, yb = np.asarray(xb, float), np.asarray(yb, float)
    xr, yr = np.asarray(xr, float), np.asarray(yr, float)
    xt, yt = np.asarray(xt, float), np.asarray(yt, float)
    xl, yl = np.asarray(xl, float), np.asarray(yl, float)

    bnd_x = np.concatenate([xb, xr, xt, xl])
    bnd_y = np.concatenate([yb, yr, yt, yl])
    ok = np.isfinite(bnd_x) & np.isfinite(bnd_y)
    if not np.any(ok):
        return

    # Background fill for this lobe (default white)
    ax.fill(bnd_x[ok], bnd_y[ok], fc=backcolor if backcolor is not None else 'w', ec='none', zorder=0)

    # Grid lines
    if grid not in ('none', 'off', 'no'):
        n_pts = 200
        lon_inner = lon_ticks[(lon_ticks > lon_min) & (lon_ticks < lon_max)]
        lat_inner = lat_ticks[(lat_ticks > lat_min) & (lat_ticks < lat_max)]

        # Meridians
        lat_pts = np.linspace(lat_min, lat_max, n_pts)
        for lon_v in lon_inner:
            x, y = m_ll2xy(np.full(n_pts, lon_v), lat_pts, clip='on')
            ax.plot(x, y, color=color, linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

        # Parallels — span the projection's lon_limits with a tiny inset so
        # clip='on' keeps every point valid regardless of center_lon.
        if full_world:
            lon_pts = np.linspace(lon_min + eps, lon_max - eps, n_pts)
        else:
            lon_pts = np.linspace(lon_min, lon_max, n_pts)
        for lat_v in lat_inner:
            x, y = m_ll2xy(lon_pts, np.full(n_pts, lat_v), clip='on')
            ax.plot(x, y, color=color, linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

    # Boundary line
    if box in ('on', 'fancy', 'yes'):
        bnd_closed_x = np.concatenate([bnd_x[ok], [bnd_x[ok][0]]])
        bnd_closed_y = np.concatenate([bnd_y[ok], [bnd_y[ok][0]]])
        ax.plot(bnd_closed_x, bnd_closed_y, 'k-', linewidth=0.5,
                clip_on=False, zorder=10)

    # Tick labels
    show_x = _labels_enabled(xticklabels)
    show_y = _labels_enabled(yticklabels)

    if show_x or show_y:
        lon_inner_l = lon_ticks[(lon_ticks > lon_min) & (lon_ticks < lon_max)]
        lat_inner_l = lat_ticks[(lat_ticks > lat_min) & (lat_ticks < lat_max)]

        x_span = float(state.x_limits[1]) - float(state.x_limits[0])
        y_span = float(state.y_limits[1]) - float(state.y_limits[0])
        lon_label_offset = y_span * 0.045
        lat_label_offset = x_span * 0.022

        if show_x:
            # Longitude labels sit where each meridian crosses a chosen parallel.
            lat_mid = 0.5 * (lat_min + lat_max)
            location = str(xaxislocation).lower()
            if location.startswith('top'):
                label_lat = lat_max
            elif location.startswith('mid'):
                label_lat = lat_mid
            else:
                label_lat = lat_min

            def _crossings(at_lat):
                out = []
                for lon_v in lon_inner_l:
                    xv, yv = m_ll2xy([lon_v], [at_lat], clip='off')
                    out.append((lon_v,
                                float(np.asarray(xv)[0]),
                                float(np.asarray(yv)[0])))
                return out

            # Some pseudocylindrical boundaries converge to a point at the poles
            # (Hammer, Mollweide, sinusoidal) and others keep a pole *line*
            # (Robinson).  Where it converges, every meridian meets lat_min at
            # the same place and the labels would stack; where it does not, the
            # bottom edge is the natural place for them and must be left alone.
            #
            # Measure the projected spacing rather than inferring it from the
            # projection name or from the latitude being near ±90°: the spacing is
            # the thing that actually matters, and it is cheap to check.  Falling
            # back to the middle of the latitude range gives the equator on a
            # whole-world map, which is what m_map's Hammer examples select with
            # m_grid('xaxis','middle').
            crossings = _crossings(label_lat)
            xs = sorted(x for _, x, y in crossings
                        if np.isfinite(x) and np.isfinite(y))
            if len(xs) > 1 and float(np.min(np.diff(xs))) < 0.02 * x_span:
                label_lat = lat_mid
                crossings = _crossings(label_lat)

            above = location.startswith('top')
            va = 'bottom' if above else 'top'
            offset = lon_label_offset if above else -lon_label_offset

            for lon_v, xv, yv in crossings:
                if not (np.isfinite(xv) and np.isfinite(yv)):
                    continue
                # Normalise to [-180, 180] so "90°E" not "-270°W"
                lon_disp = ((lon_v + 180.0) % 360.0) - 180.0
                ax.text(xv, yv + offset,
                        _fmt_lon(lon_disp),
                        ha='center', va=va,
                        fontsize=fontsize, clip_on=False, zorder=15)

        if show_y:
            for lat_v in lat_inner_l:
                xv, yv = m_ll2xy([left_lon], [lat_v], clip='off')
                xv = float(np.asarray(xv)[0])
                yv = float(np.asarray(yv)[0])
                if not (np.isfinite(xv) and np.isfinite(yv)):
                    continue
                ax.text(xv - lat_label_offset, yv,
                        _fmt_lat(lat_v),
                        ha='right', va='center',
                        fontsize=fontsize, clip_on=False, zorder=15)


# ---------------------------------------------------------------------------
# Oblique Mercator grid (curved grid lines, rectangular map box)
# ---------------------------------------------------------------------------

def _find_edge_crossing(x_curve, y_curve, edge_val, axis='y'):
    """Return the (x, y) where a projected curve first crosses a map boundary.

    axis='y': find where y_curve == edge_val (top/bottom boundary).
    axis='x': find where x_curve == edge_val (left/right boundary).
    Returns (None, None) if no crossing found.
    """
    vals  = y_curve if axis == 'y' else x_curve
    other = x_curve if axis == 'y' else y_curve
    d = np.asarray(vals, float) - edge_val
    for i in range(len(d) - 1):
        if not (np.isfinite(d[i]) and np.isfinite(d[i + 1])):
            continue
        if d[i] * d[i + 1] <= 0:
            t = abs(d[i]) / (abs(d[i]) + abs(d[i + 1]) + 1e-30)
            xi = x_curve[i] + t * (x_curve[i + 1] - x_curve[i])
            yi = y_curve[i] + t * (y_curve[i + 1] - y_curve[i])
            return float(xi), float(yi)
    return None, None


def _draw_grid_oblique(
    ax, state, box, grid, tickdir,
    lon_ticks, lat_ticks,
    xticklabels, yticklabels,
    linestyle, fontsize,
    yaxislocation='left', xaxislocation='bottom', ticklen=0.0,
):
    """
    Draw a grid for the oblique Mercator projection.

    The map boundary is a rectangle in (x, y) projected space.
    Parallels and meridians are curved lines drawn by projecting a fine grid.
    Tick marks are placed where each grid line crosses the boundary.
    """
    x0, x1 = state.x_limits
    y0, y1 = state.y_limits

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    # Hide spines, ticks, and background without calling set_axis_off(),
    # which would also hide xlabel/ylabel via xaxis.set_visible(False).
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.patch.set_visible(False)

    # White background inside the map boundary rectangle
    ax.fill([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0],
            fc='w', ec='none', zorder=0)

    if lon_ticks is None:
        lon_ticks = _nice_ticks(state.lon_limits[0], state.lon_limits[1], target=8)
    if lat_ticks is None:
        lat_ticks = _nice_ticks(state.lat_limits[0], state.lat_limits[1], target=8)

    lon_ticks = np.asarray(lon_ticks, float)
    lat_ticks = np.asarray(lat_ticks, float)

    span   = min(x1 - x0, y1 - y0)
    tk_len = float(ticklen) * span  # tick length in data units
    lat_lo, lat_hi = state.lat_limits
    lon_lo, lon_hi = state.lon_limits
    n_pts = 400

    # Extended lat/lon ranges for boundary-crossing searches.
    # Oblique meridians/parallels can cross the map boundary outside the
    # geographic bounding box, so we sweep a wider geographic range.
    lat_lo_w = max(lat_lo - 30, -89.0)
    lat_hi_w = min(lat_hi + 30,  89.0)
    lon_lo_w = max(lon_lo - 30, -180.0)
    lon_hi_w = min(lon_hi + 30,  180.0)

    # ------------------------------------------------------------------
    # Curved grid lines (clipped to the projected map box)
    # ------------------------------------------------------------------
    draw_lines = grid not in ('none', 'off', 'no', 'n')

    lat_pts = np.linspace(lat_lo_w, lat_hi_w, n_pts)
    lon_pts = np.linspace(lon_lo_w, lon_hi_w, n_pts)

    if draw_lines:
        for lon_v in lon_ticks:
            x, y = m_ll2xy(np.full(n_pts, lon_v), lat_pts, clip='on')
            ax.plot(x, y, color='k', linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)
        for lat_v in lat_ticks:
            x, y = m_ll2xy(lon_pts, np.full(n_pts, lat_v), clip='on')
            ax.plot(x, y, color='k', linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

    # ------------------------------------------------------------------
    # Boundary rectangle
    # ------------------------------------------------------------------
    if box in ('on', 'yes', 'fancy'):
        ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0],
                'k-', linewidth=1.0, clip_on=False, zorder=10)

    # ------------------------------------------------------------------
    # Tick marks and labels
    # ------------------------------------------------------------------
    show_x = _labels_enabled(xticklabels)
    show_y = _labels_enabled(yticklabels)
    fs = fontsize

    # The sign of the outward tick direction depends on tickdir:
    tick_sign = 1 if tickdir == 'out' else -1

    # --- Longitude ticks on top or bottom ---
    y_lon_edge = y1 if xaxislocation.startswith('top') else y0
    ny_lon     = tick_sign * (1 if xaxislocation.startswith('top') else -1)
    va_lon     = 'bottom' if xaxislocation.startswith('top') else 'top'
    label_gap  = 0.015 * span

    for lon_v in lon_ticks:
        xc, yc = m_ll2xy(np.full(n_pts, lon_v), lat_pts, clip='off')
        xc, yc = np.asarray(xc, float), np.asarray(yc, float)
        xi, yi = _find_edge_crossing(xc, yc, y_lon_edge, axis='y')
        if xi is None or not np.isfinite(xi) or not (x0 <= xi <= x1):
            continue
        if tk_len > 0:
            ax.plot([xi, xi], [y_lon_edge, y_lon_edge + ny_lon * tk_len],
                    'k-', linewidth=0.5, clip_on=False, zorder=10)
        if show_x:
            ax.text(xi, y_lon_edge + ny_lon * (tk_len + label_gap),
                    _fmt_lon(lon_v), ha='center', va=va_lon,
                    fontsize=fs, clip_on=False)

    # --- Latitude ticks on left or right ---
    x_lat_edge = x1 if yaxislocation.startswith('right') else x0
    nx_lat     = tick_sign * (1 if yaxislocation.startswith('right') else -1)
    ha_lat     = 'left' if yaxislocation.startswith('right') else 'right'

    for lat_v in lat_ticks:
        xc, yc = m_ll2xy(lon_pts, np.full(n_pts, lat_v), clip='off')
        xc, yc = np.asarray(xc, float), np.asarray(yc, float)
        xi, yi = _find_edge_crossing(xc, yc, x_lat_edge, axis='x')
        if yi is None or not np.isfinite(yi) or not (y0 <= yi <= y1):
            continue
        if tk_len > 0:
            ax.plot([x_lat_edge, x_lat_edge + nx_lat * tk_len], [yi, yi],
                    'k-', linewidth=0.5, clip_on=False, zorder=10)
        if show_y:
            ax.text(x_lat_edge + nx_lat * (tk_len + label_gap), yi,
                    _fmt_lat(lat_v), ha=ha_lat, va='center',
                    fontsize=fs, clip_on=False)


# ---------------------------------------------------------------------------
# Rectangular grid (equidistant cylindrical, etc.)
# ---------------------------------------------------------------------------

def _draw_grid_rectangular(
    ax, state, box, grid, tickdir,
    lon_ticks, lat_ticks,
    xticklabels, yticklabels,
    linestyle, fontsize,
    linewidth: float = 1.0,
    grid_color: str = 'k',
    backcolor=None,
    boxstyle: str = 'fill',
    xaxislocation: str = 'bottom',
    yaxislocation: str = 'left',
):
    x0, x1 = state.x_limits
    y0, y1 = state.y_limits

    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect('equal')
    ax.set_axis_off()

    if backcolor is not None:
        ax.fill([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0],
                fc=backcolor, ec='none', zorder=0)

    if lon_ticks is None:
        lon_ticks = _nice_ticks(state.lon_limits[0], state.lon_limits[1], target=6)
    if lat_ticks is None:
        lat_ticks = _nice_ticks(state.lat_limits[0], state.lat_limits[1], target=6)

    lon_ticks = np.asarray(lon_ticks, dtype=float)
    lat_ticks = np.asarray(lat_ticks, dtype=float)

    mean_lat = np.mean(state.lat_limits)
    mean_lon = np.mean(state.lon_limits)

    x_ticks = np.array([
        float(m_ll2xy([lv], [mean_lat], clip='off')[0][0])
        for lv in lon_ticks
    ])
    y_ticks = np.array([
        float(m_ll2xy([mean_lon], [lv], clip='off')[1][0])
        for lv in lat_ticks
    ])

    lon_in = (lon_ticks >= state.lon_limits[0]) & (lon_ticks <= state.lon_limits[1])
    lat_in = (lat_ticks >= state.lat_limits[0]) & (lat_ticks <= state.lat_limits[1])
    x_ticks_in = x_ticks[lon_in]
    y_ticks_in = y_ticks[lat_in]
    lon_ticks_in = lon_ticks[lon_in]
    lat_ticks_in = lat_ticks[lat_in]

    span = min(x1 - x0, y1 - y0)
    bw = span * 0.015

    # Grid lines
    if grid not in ('none', 'off', 'no'):
        for xt in x_ticks_in:
            ax.plot([xt, xt], [y0, y1], color=grid_color, linewidth=0.4,
                    linestyle=linestyle, zorder=2, clip_on=True)
        for yt in y_ticks_in:
            ax.plot([x0, x1], [yt, yt], color=grid_color, linewidth=0.4,
                    linestyle=linestyle, zorder=2, clip_on=True)

    # Frame / box
    if box == 'fancy':
        _draw_fancy_box(ax, x0, x1, y0, y1, x_ticks_in, y_ticks_in, bw, style=boxstyle)
        state.title_y = 1.0 + bw / (y1 - y0) + 0.01
        if ax.get_title():
            ax.set_title(ax.get_title(), y=state.title_y)
    elif box in ('on', 'yes'):
        _draw_simple_box(ax, x0, x1, y0, y1, linewidth=linewidth)

    # Outward tick marks — suppressed when box='fancy' (ruler/fill box encodes ticks)
    tick_size = bw * 0.7
    if tickdir == 'out' and box != 'fancy':
        y_xtick = y1 if xaxislocation == 'top' else y0
        xt_sign = 1 if xaxislocation == 'top' else -1
        for xt in x_ticks_in:
            ax.plot([xt, xt], [y_xtick, y_xtick + xt_sign * tick_size],
                    'k-', linewidth=0.5, zorder=10, clip_on=False)

        x_ytick = x1 if yaxislocation == 'right' else x0
        yt_sign = 1 if yaxislocation == 'right' else -1
        for yt in y_ticks_in:
            ax.plot([x_ytick, x_ytick + yt_sign * tick_size], [yt, yt],
                    'k-', linewidth=0.5, zorder=10, clip_on=False)

    # Tick labels
    show_x = _labels_enabled(xticklabels)
    show_y = _labels_enabled(yticklabels)

    label_offset = bw * 0.6 if box != 'off' else bw * 0.2
    if tickdir == 'out':
        label_offset += bw * 0.5

    fs = fontsize

    if show_x:
        if xaxislocation == 'top':
            for xt, lv in zip(x_ticks_in, lon_ticks_in):
                ax.text(xt, y1 + bw + label_offset, _fmt_lon(lv),
                        ha='center', va='bottom', fontsize=fs, clip_on=False)
        else:
            for xt, lv in zip(x_ticks_in, lon_ticks_in):
                ax.text(xt, y0 - bw - label_offset, _fmt_lon(lv),
                        ha='center', va='top', fontsize=fs, clip_on=False)

    if show_y:
        if yaxislocation == 'right':
            for yt, lv in zip(y_ticks_in, lat_ticks_in):
                ax.text(x1 + bw + label_offset, yt, _fmt_lat(lv),
                        ha='left', va='center', fontsize=fs, clip_on=False)
        else:
            for yt, lv in zip(y_ticks_in, lat_ticks_in):
                ax.text(x0 - bw - label_offset, yt, _fmt_lat(lv),
                        ha='right', va='center', fontsize=fs, clip_on=False)


# ---------------------------------------------------------------------------
# Circular grid (orthographic, stereographic, etc.)
# ---------------------------------------------------------------------------

def _draw_grid_circular(
    ax, state, box, grid,
    lon_ticks, lat_ticks,
    xticklabels, yticklabels,
    linestyle, fontsize,
    lat_label_lon=None,
    grid_color='k',
):
    R = abs(state.x_limits[1])  # hemisphere radius in metres

    ax.set_xlim(-R * 1.02, R * 1.02)
    ax.set_ylim(-R * 1.02, R * 1.02)
    ax.set_aspect('equal')
    ax.set_axis_off()

    # White fill inside the globe circle
    theta = np.linspace(0, 2 * np.pi, 361)
    circle_x = R * np.cos(theta)
    circle_y = R * np.sin(theta)
    ax.fill(circle_x, circle_y, fc='w', ec='none', zorder=-1)

    # Auto-generate ticks within the visible region
    if lon_ticks is None:
        lon_lo_v = float(state.lon_limits[0])
        lon_hi_v = float(state.lon_limits[1])
        if lon_hi_v - lon_lo_v >= 340:
            lon_ticks = _nice_ticks(-180.0, 180.0, target=12)
        else:
            lon_ticks = _nice_ticks(lon_lo_v, lon_hi_v, target=6)
    if lat_ticks is None:
        lat_lo_v = float(state.lat_limits[0])
        lat_hi_v = float(state.lat_limits[1])
        if lat_hi_v - lat_lo_v >= 160:
            lat_ticks = _nice_ticks(-80.0, 80.0, target=5)
        else:
            lat_ticks = _nice_ticks(lat_lo_v, lat_hi_v, target=4)

    lon_ticks = np.asarray(lon_ticks, dtype=float)
    lat_ticks = np.asarray(lat_ticks, dtype=float)

    # Grid lines — curved for the circular projection
    lon_lo_g = float(state.lon_limits[0])
    lon_hi_g = float(state.lon_limits[1])
    lat_lo_g = max(float(state.lat_limits[0]), -89.0)
    lat_hi_g = min(float(state.lat_limits[1]),  89.0)
    # For full-globe lon range sample all 360°; otherwise just the visible span
    if lon_hi_g - lon_lo_g >= 340:
        lon_sample = np.linspace(-180, 180, 721)
    else:
        lon_sample = np.linspace(lon_lo_g, lon_hi_g, 361)

    if grid not in ('none', 'off', 'no'):
        # Parallels (latitude lines)
        for lat_val in lat_ticks:
            x, y = m_ll2xy(lon_sample, np.full_like(lon_sample, lat_val), clip='on')
            ax.plot(x, y, color=grid_color, linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

        # Meridians (longitude lines)
        n_lat = min(max(int((lat_hi_g - lat_lo_g) * 5), 50), 500)
        lat_pts = np.linspace(lat_lo_g, lat_hi_g, n_lat)
        for lon_val in lon_ticks:
            x, y = m_ll2xy(np.full_like(lat_pts, lon_val), lat_pts, clip='on')
            ax.plot(x, y, color=grid_color, linewidth=0.4, linestyle=linestyle,
                    zorder=2, clip_on=True)

    # Circular boundary
    if box in ('on', 'fancy', 'yes'):
        ax.plot(circle_x, circle_y, 'k-', linewidth=1.0,
                clip_on=False, zorder=10)

    # Tick labels on the perimeter (suppressed by default for circular maps)
    # Only draw if explicitly enabled via xticklabels / yticklabels
    show_x = _labels_enabled(xticklabels)
    show_y = _labels_enabled(yticklabels)

    if show_x or show_y:
        _draw_circular_labels(ax, state, lon_ticks, lat_ticks,
                              show_x, show_y, R, fontsize,
                              lat_label_lon=lat_label_lon)


def _draw_circular_labels(ax, state, lon_ticks, lat_ticks,
                           show_x, show_y, R, fontsize,
                           lat_label_lon=None):
    """
    Place lon/lat labels at points where gridlines cross the map boundary
    circle.  Works for both full-hemisphere and zoomed circular projections.

    For each meridian the bottom boundary crossing is used for the longitude
    label; for each parallel the left boundary crossing is used for the
    latitude label.  A threshold of r > 0.65*R filters gridlines that stay
    entirely in the map interior.
    """
    fs = fontsize
    pad = R * 0.04  # label offset outside the circle

    #: Final positions of labels already drawn, so later ones can avoid them.
    placed_positions: list[tuple[float, float]] = []
    #: Two labels closer than this on screen read as a single blob.
    min_label_gap = R * 0.07

    def _label_position(xb, yb, snap_to_boundary=True):
        """Final (x, y) for a label anchored on the ray through (xb, yb)."""
        rb = np.hypot(xb, yb)
        if rb < 1e-10:
            return None
        nx, ny = xb / rb, yb / rb
        r_out = (R if snap_to_boundary else rb) + pad
        return r_out * nx, r_out * ny, nx, ny

    def _collides(xl, yl):
        return any(np.hypot(xl - px, yl - py) < min_label_gap
                   for px, py in placed_positions)

    def _place_label(xb, yb, text, snap_to_boundary=True):
        """
        Place text just outside the map, on the ray through (xb, yb).

        `snap_to_boundary` pushes the label out to the boundary circle.  That is
        right for labels derived from a boundary crossing, where it just absorbs
        interpolation error.  It is wrong for labels positioned along a chosen
        meridian: several parallels share one ray, so snapping collapses them all
        onto the same point.  Pass False to keep each label at its own radius.

        Labels are horizontal, not tangential.  A tangential rotation is forced
        to ±90° at the left and right extremes of the circle, and normalising it
        into (-90°, 90°] cannot make those two agree: the right-hand label ends
        up reading bottom-to-top and the left-hand one top-to-bottom, so the
        left one looks inverted.  There is no rotation rule that is both
        continuous around the circle and never upside-down.

        Horizontal text avoids the problem outright.  What the rotation was also
        buying — keeping the text clear of the boundary — is recovered by
        anchoring each label on the side facing the map, so it grows outward.
        """
        got = _label_position(xb, yb, snap_to_boundary)
        if got is None:
            return
        xl, yl, nx, ny = got
        # Anchor away from the map: at the left edge the text's right end sits on
        # the anchor, at the top its bottom does, and so on.
        ha = 'right' if nx < -0.25 else ('left' if nx > 0.25 else 'center')
        va = 'top' if ny < -0.25 else ('bottom' if ny > 0.25 else 'center')
        ax.text(xl, yl, text, ha=ha, va=va,
                rotation=0, fontsize=fs, clip_on=False)
        placed_positions.append((xl, yl))

    lat_lo = max(float(state.lat_limits[0]), -89.9)
    lat_hi = min(float(state.lat_limits[1]),  89.9)
    lon_lo = float(state.lon_limits[0])
    lon_hi = float(state.lon_limits[1])

    # ------------------------------------------------------------------
    # Longitude labels: find each meridian's bottom boundary crossing
    # ------------------------------------------------------------------
    if show_x:
        # ±180° is one meridian; without this it is labelled twice, on top of
        # itself, whenever the tick list contains both ends.
        labelled_lons: set[float] = set()
        for lon_val in lon_ticks:
            key = round(((float(lon_val) + 180.0) % 360.0) - 180.0, 6)
            if key in labelled_lons:
                continue
            labelled_lons.add(key)
            lats = np.linspace(lat_lo, lat_hi, 200)
            xm, ym = m_ll2xy(np.full_like(lats, lon_val), lats, clip='off')
            xm = np.asarray(xm, float)
            ym = np.asarray(ym, float)
            r = np.hypot(xm, ym)
            inside = np.isfinite(r) & (r <= R * 1.001)
            if not np.any(inside):
                continue
            # Bottom-most inside point: minimum projected y
            ym_in = ym[inside]
            xm_in = xm[inside]
            rm_in = r[inside]
            bottom_i = np.argmin(ym_in)
            xb, yb = float(xm_in[bottom_i]), float(ym_in[bottom_i])
            # Only label a meridian that actually reaches the map boundary.  On a
            # non-polar circular map, meridians on the far hemisphere still have a
            # visible sliver, because every meridian converges at the poles and a
            # pole can be in view — their lowest visible point is that pole, well
            # inside the boundary.  Measured for ortho(48N, 123W): meridians that
            # genuinely cross the limb bottom out at r/R = 0.996-1.001, while the
            # four far-side ones bottom out at the north pole, r/R = 0.672.  The
            # threshold has to sit between those; it used to be 0.65, which let all
            # four through and stacked their labels on the pole.
            if rm_in[bottom_i] < R * 0.9:
                continue
            _place_label(xb, yb, _fmt_lon(lon_val))

    # ------------------------------------------------------------------
    # Latitude labels: find each parallel's left boundary crossing
    # ------------------------------------------------------------------
    if show_y:
        if lat_label_lon is not None:
            # Explicit meridian requested: project and label directly
            for lat_val in lat_ticks:
                x, y = m_ll2xy([lat_label_lon], [lat_val], clip='off')
                xv, yv = float(np.asarray(x)[0]), float(np.asarray(y)[0])
                if not (np.isfinite(xv) and np.isfinite(yv)):
                    continue
                if np.hypot(xv, yv) < R * 0.65:
                    continue
                # Every parallel sits on the same ray here, so keep each at its
                # own radius rather than snapping them all to the boundary.
                _place_label(xv, yv, _fmt_lat(lat_val), snap_to_boundary=False)
        else:
            for lat_val in lat_ticks:
                lons_p = np.linspace(lon_lo, lon_hi, 200)
                xp, yp = m_ll2xy(lons_p, np.full_like(lons_p, lat_val), clip='off')
                xp = np.asarray(xp, float)
                yp = np.asarray(yp, float)
                r = np.hypot(xp, yp)
                inside = np.isfinite(r) & (r <= R * 1.001)
                if not np.any(inside):
                    continue
                # Left-most inside point: minimum projected x
                xi = xp[inside]
                yi = yp[inside]
                ri = r[inside]
                # Prefer the left-most point, then work rightwards along the
                # parallel.  A parallel that reaches the map boundary meets it
                # exactly where the left-most meridian's label is placed, so the
                # two would be drawn on top of each other; sliding along the
                # parallel keeps the label on the line it names, which displacing
                # it radially or by a fixed angle would not.
                order = np.argsort(xi)
                for cand in order:
                    if ri[cand] < R * 0.65:
                        continue
                    xl, yl = float(xi[cand]), float(yi[cand])
                    got = _label_position(xl, yl, snap_to_boundary=False)
                    if got is None:
                        continue
                    if _collides(got[0], got[1]):
                        continue
                    # Same reason as the explicit-meridian branch above: on a
                    # polar map the parallels are concentric circles, so their
                    # points sit at different radii (60°N at 0.75 R, 50°N at
                    # 0.85 R) and must not be snapped to the boundary.
                    _place_label(xl, yl, _fmt_lat(lat_val),
                                 snap_to_boundary=False)
                    break


# ---------------------------------------------------------------------------
# Box helpers (rectangular)
# ---------------------------------------------------------------------------

def _draw_simple_box(ax, x0, x1, y0, y1, linewidth: float = 1.0):
    r = Rectangle(
        (x0, y0), x1 - x0, y1 - y0,
        fill=False, edgecolor='k', linewidth=linewidth,
        clip_on=False, zorder=10,
    )
    ax.add_patch(r)


def _draw_fancy_corner(ax, cx, cy, dx, dy, c_h, c_v, diag_offset_y=0):
    """
    Draw one corner of the fancy box.

    (cx, cy)  inner corner of the map box.
    (dx, dy)  signed offset to the outer corner (each ±bw).
    c_h       terminal colour of the adjacent horizontal edge strip.
    c_v       terminal colour of the adjacent vertical edge strip.
    diag_offset_y  shift the diagonal separator by this many display pixels in y
                   (positive = up on screen).  Use +1 for corners where dx and dy
                   have the same sign (BL and TR) to correct AGG rasterisation of
                   positive-slope diagonals.

    When both colours are the same the corner is a solid square; a pixel-snapped
    diagonal line is drawn so white-on-white corners have a visible separator.
    When they differ, the square is filled with c_h and the vertical-edge-adjacent
    triangle is overwritten with c_v, creating a pixel-precise chevron seam — no
    separate plot() diagonal is needed or drawn.
    """
    lw = 0.4
    sq_x = [cx, cx + dx, cx + dx, cx]
    sq_y = [cy, cy, cy + dy, cy + dy]
    [p] = ax.fill(sq_x, sq_y, fc=c_h, ec='none', clip_on=False, zorder=10)
    p.set_antialiased(False)
    if c_h != c_v:
        # Triangle that borders the vertical edge strip (two vertices at x=cx+dx)
        [p2] = ax.fill([cx, cx + dx, cx + dx],
                       [cy, cy,      cy + dy],
                       fc=c_v, ec='none', clip_on=False, zorder=10)
        p2.set_antialiased(False)
    # Diagonal separator — only needed when both colours match (the chevron fill
    # already produces a pixel-precise seam when they differ, and a redundant
    # antialiased plot() on top of it causes the 1-px misalignment artefact).
    if c_h == c_v:
        if diag_offset_y != 0:
            pts = ax.transData.transform([[cx, cy], [cx + dx, cy + dy]])
            pts[:, 1] += diag_offset_y
            start, end = ax.transData.inverted().transform(pts)
            y_start, y_end = start[1], end[1]
        else:
            y_start, y_end = cy, cy + dy
        ax.plot([cx, cx + dx], [y_start, y_end],
                color='k', linewidth=lw, antialiased=True,
                solid_capstyle='butt', clip_on=False, zorder=12)


def _draw_ruler_corner(ax, cx, cy, dx, dy, c_h, c_v, lw, diag_offset_y=0,
                       tick_at_h=False, tick_at_v=False):
    """
    Ruler-style corner: always white fill; diagonal line always drawn.

    c_h: colour of the adjacent horizontal edge strip (bottom/top).
    c_v: colour of the adjacent vertical edge strip (left/right).

    Whether the corner is its own box depends on the ticks, and that decides the
    half-line to the diagonal too.  Treating each of the two edges separately:

    * **A tick falls at the corner** (tick_at_h for an x-tick at the corner x,
      tick_at_v for a y-tick at the corner y).  The corner is delimited: a
      separator is drawn along that inner edge — the main separator loop cannot
      place it, since that only covers interior breaks.  The corner triangle is
      then a fresh box continuing the alternation, so it carries a line to the
      diagonal only when the strip beside it is *empty*.

    * **No tick there.**  Nothing delimits the corner, so the adjacent strip's
      style simply runs on into it as far as the diagonal.  The line is drawn
      only when that strip is *full*, continuing its centre line.

    The condition therefore inverts between the two cases, which is why a frame
    whose edges do not all end on a tick — the common case, since the tick step
    rarely divides the range exactly — gets a different corner treatment on each
    side.

    diag_offset_y: shift the diagonal by this many display pixels in y
    (positive = up on screen).
    """
    sq_x = [cx, cx + dx, cx + dx, cx]
    sq_y = [cy, cy, cy + dy, cy + dy]
    [p] = ax.fill(sq_x, sq_y, fc='white', ec='none', clip_on=False, zorder=10)
    p.set_antialiased(False)
    if diag_offset_y != 0:
        pts = ax.transData.transform([[cx, cy], [cx + dx, cy + dy]])
        pts[:, 1] += diag_offset_y
        start, end = ax.transData.inverted().transform(pts)
        y_start, y_end = start[1], end[1]
    else:
        y_start, y_end = cy, cy + dy
    ax.plot([cx, cx + dx], [y_start, y_end],
            color='k', linewidth=lw, antialiased=True,
            solid_capstyle='butt', clip_on=False, zorder=12)
    # Separators delimiting the corner box, drawn only where a tick lands on it.
    if tick_at_h:
        ax.plot([cx, cx], [cy, cy + dy], 'k-', lw=lw,
                antialiased=False, solid_capstyle='butt', clip_on=False, zorder=12)
    if tick_at_v:
        ax.plot([cx, cx + dx], [cy, cy], 'k-', lw=lw,
                antialiased=False, solid_capstyle='butt', clip_on=False, zorder=12)

    # Half-lines from the inner corner edges to the diagonal midpoint, where both
    # terminate.  Delimited by a tick -> a new box, so drawn when the neighbouring
    # strip is empty.  Not delimited -> the neighbour's style continues into the
    # corner, so drawn when that strip is full.  See the docstring.
    mx = cx + dx / 2.0
    my = cy + dy / 2.0
    draw_h = (c_h != 'k') if tick_at_h else (c_h == 'k')
    draw_v = (c_v != 'k') if tick_at_v else (c_v == 'k')
    if draw_h:
        ax.plot([cx, mx], [my, my], 'k-', lw=lw,
                antialiased=False, solid_capstyle='butt', clip_on=False, zorder=12)
    if draw_v:
        ax.plot([mx, mx], [cy, my], 'k-', lw=lw,
                antialiased=False, solid_capstyle='butt', clip_on=False, zorder=12)


def _draw_ruler_box(ax, x0, x1, y0, y1, x_ticks, y_ticks, bw):
    """
    Ruler-style fancy border.

    Mirrors the fill-style logic exactly: same alternating black/white strips
    and chevron corners.  White patches are filled white as normal.  Black
    patches are replaced by a white fill with a thin black centre line running
    along the middle of the strip (at bw/2 from the map edge).  Separator lines
    are drawn at every patch boundary, and centre lines extend to the corner
    diagonal intersection.
    """
    lw = 0.4
    hw = bw / 2.0

    x_breaks = np.unique(np.concatenate([
        [x0], x_ticks[(x_ticks > x0) & (x_ticks < x1)], [x1],
    ]))
    y_breaks = np.unique(np.concatenate([
        [y0], y_ticks[(y_ticks > y0) & (y_ticks < y1)], [y1],
    ]))

    def _rect(xa, ya, w, h, color):
        ax.add_patch(Rectangle(
            (xa, ya), w, h,
            facecolor=color, edgecolor='none',
            clip_on=False, zorder=10,
            antialiased=False,
        ))

    def _strip(xa, ya, w, h, color, lx0, lx1, ly0, ly1):
        """White fill; if black, add the centre line from (lx0,ly0)→(lx1,ly1)."""
        _rect(xa, ya, w, h, 'white')
        if color == 'k':
            ax.plot([lx0, lx1], [ly0, ly1], 'k-', lw=lw,
                    antialiased=False, solid_capstyle='butt',
                    clip_on=False, zorder=12)

    n_x = len(x_breaks) - 1
    n_y = len(y_breaks) - 1

    # Bottom edge
    c_bottom_left = c_bottom_right = 'k'
    idx = 0
    for i, (xa, xb) in enumerate(zip(x_breaks[:-1], x_breaks[1:])):
        mid = (xa + xb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_bottom_left = c1
        _strip(xa, y0 - bw, mid - xa, bw, c1,  xa, mid, y0 - hw, y0 - hw)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_x - 1:
            c_bottom_right = c2
        _strip(mid, y0 - bw, xb - mid, bw, c2,  mid, xb, y0 - hw, y0 - hw)
        idx += 1

    # Top edge
    c_top_left = c_top_right = 'k'
    idx = 0
    for i, (xa, xb) in enumerate(zip(x_breaks[:-1], x_breaks[1:])):
        mid = (xa + xb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_top_left = c1
        _strip(xa, y1, mid - xa, bw, c1,  xa, mid, y1 + hw, y1 + hw)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_x - 1:
            c_top_right = c2
        _strip(mid, y1, xb - mid, bw, c2,  mid, xb, y1 + hw, y1 + hw)
        idx += 1

    # Left edge
    c_left_bottom = c_left_top = 'k'
    idx = 1
    for i, (ya, yb) in enumerate(zip(y_breaks[:-1], y_breaks[1:])):
        mid = (ya + yb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_left_bottom = c1
        _strip(x0 - bw, ya, bw, mid - ya, c1,  x0 - hw, x0 - hw, ya, mid)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_y - 1:
            c_left_top = c2
        _strip(x0 - bw, mid, bw, yb - mid, c2,  x0 - hw, x0 - hw, mid, yb)
        idx += 1

    # Right edge
    c_right_bottom = c_right_top = 'k'
    idx = 1
    for i, (ya, yb) in enumerate(zip(y_breaks[:-1], y_breaks[1:])):
        mid = (ya + yb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_right_bottom = c1
        _strip(x1, ya, bw, mid - ya, c1,  x1 + hw, x1 + hw, ya, mid)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_y - 1:
            c_right_top = c2
        _strip(x1, mid, bw, yb - mid, c2,  x1 + hw, x1 + hw, mid, yb)
        idx += 1

    # Separator lines at every patch boundary
    x_seps = sorted(
        list(x_breaks[1:-1]) +
        [(x_breaks[i] + x_breaks[i + 1]) / 2.0 for i in range(n_x)]
    )
    for xs in x_seps:
        ax.plot([xs, xs], [y0 - bw, y0], 'k-', lw=lw,
                antialiased=False, solid_capstyle='projecting',
                clip_on=False, zorder=12)
        ax.plot([xs, xs], [y1, y1 + bw], 'k-', lw=lw,
                antialiased=False, solid_capstyle='projecting',
                clip_on=False, zorder=12)

    y_seps = sorted(
        list(y_breaks[1:-1]) +
        [(y_breaks[i] + y_breaks[i + 1]) / 2.0 for i in range(n_y)]
    )
    for ys in y_seps:
        ax.plot([x0 - bw, x0], [ys, ys], 'k-', lw=lw,
                antialiased=False, solid_capstyle='projecting',
                clip_on=False, zorder=12)
        ax.plot([x1, x1 + bw], [ys, ys], 'k-', lw=lw,
                antialiased=False, solid_capstyle='projecting',
                clip_on=False, zorder=12)

    # Corners — detect ticks that fall exactly on a corner coordinate
    x_at_x0 = bool(np.any(np.isclose(x_ticks, x0)))
    x_at_x1 = bool(np.any(np.isclose(x_ticks, x1)))
    y_at_y0 = bool(np.any(np.isclose(y_ticks, y0)))
    y_at_y1 = bool(np.any(np.isclose(y_ticks, y1)))

    _draw_ruler_corner(ax, x0, y0, -bw, -bw, c_bottom_left,  c_left_bottom,  lw,
                       tick_at_h=x_at_x0, tick_at_v=y_at_y0)
    _draw_ruler_corner(ax, x1, y0, +bw, -bw, c_bottom_right, c_right_bottom, lw,
                       tick_at_h=x_at_x1, tick_at_v=y_at_y0)
    _draw_ruler_corner(ax, x1, y1, +bw, +bw, c_top_right,    c_right_top,    lw,
                       tick_at_h=x_at_x1, tick_at_v=y_at_y1)
    _draw_ruler_corner(ax, x0, y1, -bw, +bw, c_top_left,     c_left_top,     lw,
                       tick_at_h=x_at_x0, tick_at_v=y_at_y1)

    # Outer border + inner border
    ax.add_patch(Rectangle(
        (x0 - bw, y0 - bw), x1 - x0 + 2 * bw, y1 - y0 + 2 * bw,
        fill=False, edgecolor='k', linewidth=lw,
        clip_on=False, zorder=11, antialiased=False,
    ))
    ax.add_patch(Rectangle(
        (x0, y0), x1 - x0, y1 - y0,
        fill=False, edgecolor='k', linewidth=lw,
        clip_on=False, zorder=11, antialiased=False,
    ))


def _draw_fancy_box(ax, x0, x1, y0, y1, x_ticks, y_ticks, bw, style: str = 'fill'):
    """
    Fancy border in one of two styles:

    'fill' (default) — alternating solid black/white strips with chevron corners.
    'line'           — centre line along each edge + perpendicular tick marks at
                       every lat/lon tick position; no filled patches.
    """
    if style == 'line':
        _draw_ruler_box(ax, x0, x1, y0, y1, x_ticks, y_ticks, bw)
        return
    lw = 0.4

    x_breaks = np.unique(np.concatenate([
        [x0],
        x_ticks[(x_ticks > x0) & (x_ticks < x1)],
        [x1],
    ]))
    y_breaks = np.unique(np.concatenate([
        [y0],
        y_ticks[(y_ticks > y0) & (y_ticks < y1)],
        [y1],
    ]))

    n_x = len(x_breaks) - 1
    n_y = len(y_breaks) - 1

    black_rects = []
    white_rects = []

    def _collect_rect(xa, ya, w, h, color):
        verts = np.array([[xa, ya], [xa + w, ya], [xa + w, ya + h], [xa, ya + h]])
        if color == 'k':
            black_rects.append(verts)
        else:
            white_rects.append(verts)

    # Bottom edge (outer y = y0-bw, inner y = y0) — rectangles only, no corner ext.
    c_bottom_left = c_bottom_right = 'k'
    idx = 0
    for i, (xa, xb) in enumerate(zip(x_breaks[:-1], x_breaks[1:])):
        mid = (xa + xb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_bottom_left = c1
        _collect_rect(xa, y0 - bw, mid - xa, bw, c1)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_x - 1:
            c_bottom_right = c2
        _collect_rect(mid, y0 - bw, xb - mid, bw, c2)
        idx += 1

    # Top edge (outer y = y1+bw, inner y = y1)
    c_top_left = c_top_right = 'k'
    idx = 0
    for i, (xa, xb) in enumerate(zip(x_breaks[:-1], x_breaks[1:])):
        mid = (xa + xb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_top_left = c1
        _collect_rect(xa, y1, mid - xa, bw, c1)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_x - 1:
            c_top_right = c2
        _collect_rect(mid, y1, xb - mid, bw, c2)
        idx += 1

    # Left edge (outer x = x0-bw, inner x = x0)
    c_left_bottom = c_left_top = 'k'
    idx = 1
    for i, (ya, yb) in enumerate(zip(y_breaks[:-1], y_breaks[1:])):
        mid = (ya + yb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_left_bottom = c1
        _collect_rect(x0 - bw, ya, bw, mid - ya, c1)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_y - 1:
            c_left_top = c2
        _collect_rect(x0 - bw, mid, bw, yb - mid, c2)
        idx += 1

    # Right edge (outer x = x1+bw, inner x = x1)
    c_right_bottom = c_right_top = 'k'
    idx = 1
    for i, (ya, yb) in enumerate(zip(y_breaks[:-1], y_breaks[1:])):
        mid = (ya + yb) / 2.0
        c1 = 'k' if idx % 2 == 0 else 'white'
        if i == 0:
            c_right_bottom = c1
        _collect_rect(x1, ya, bw, mid - ya, c1)
        idx += 1
        c2 = 'k' if idx % 2 == 0 else 'white'
        if i == n_y - 1:
            c_right_top = c2
        _collect_rect(x1, mid, bw, yb - mid, c2)
        idx += 1

    from matplotlib.collections import PolyCollection
    if black_rects:
        ax.add_collection(PolyCollection(black_rects, facecolor='k', edgecolor='none',
                                         clip_on=False, zorder=10, antialiased=False))
    if white_rects:
        ax.add_collection(PolyCollection(white_rects, facecolor='white', edgecolor='none',
                                         clip_on=False, zorder=10, antialiased=False))

    # Corners — solid square when same colour, chevron when different
    _draw_fancy_corner(ax, x0, y0, -bw, -bw, c_bottom_left,  c_left_bottom)   # BL
    _draw_fancy_corner(ax, x1, y0, +bw, -bw, c_bottom_right, c_right_bottom)  # BR
    _draw_fancy_corner(ax, x1, y1, +bw, +bw, c_top_right,    c_right_top)     # TR
    _draw_fancy_corner(ax, x0, y1, -bw, +bw, c_top_left,     c_left_top)      # TL

    # Outer border around the full fancy box (including corner areas)
    ax.add_patch(Rectangle(
        (x0 - bw, y0 - bw), x1 - x0 + 2 * bw, y1 - y0 + 2 * bw,
        fill=False, edgecolor='k', linewidth=lw,
        clip_on=False, zorder=11, antialiased=False,
    ))
    # Inner border at the map edge
    ax.add_patch(Rectangle(
        (x0, y0), x1 - x0, y1 - y0,
        fill=False, edgecolor='k', linewidth=lw,
        clip_on=False, zorder=11, antialiased=False,
    ))
