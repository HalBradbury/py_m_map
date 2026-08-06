"""
Custom colourbar for contourf / shaded-relief plots.

m_contfbar — ported from m_contfbar.m
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import Normalize, ListedColormap, BoundaryNorm
from matplotlib.contour import ContourSet


def _colour_source(ax):
    """
    The artist whose colour mapping a colourbar should describe.

    m_contourf draws its filled bands and then lays black contour *lines* over
    them, so the most recent artist is usually that overlay — an unfilled
    ContourSet carrying a single-colour map.  Reading the colormap or the colour
    limits from it produces a uniformly black colourbar, so unfilled contour sets
    are skipped in favour of the artist that actually maps data to colour.

    Returns None when nothing colour-mapped has been plotted.
    """
    for artist in reversed(list(ax.collections) + list(ax.images)):
        if isinstance(artist, ContourSet) and not artist.filled:
            continue
        return artist
    return None


def _nice_cbar_ticks(lo: float, hi: float, target: int = 6) -> np.ndarray:
    """Return ~`target` round tick values spanning [lo, hi]."""
    span = hi - lo
    if span == 0:
        return np.array([lo])
    candidates = [1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000]
    step = min(candidates, key=lambda s: abs(span / s - target))
    start = np.ceil(lo / step) * step
    stop = np.floor(hi / step) * step
    ticks = np.arange(start, stop + step * 1e-6, step)
    return ticks[(ticks >= lo - 1e-6) & (ticks <= hi + 1e-6)]


def m_contfbar(
    xpos,
    ypos,
    data,
    levels,
    *,
    colormap=None,
    caxis: tuple | None = None,
    axfrac: float = 0.03,
    endpiece: bool = True,
    extend: str | None = None,
    levels_mode: str = 'set',
    edgecolor: str | None = None,
    fontsize: float | None = None,
    discrete: bool | None = None,
    **kwargs,
):
    """
    Draw a colourbar positioned relative to the current axes.

    Closely follows m_contfbar.m: the bar spans exactly the contoured
    levels, with optional triangular end-pieces indicating out-of-range data.

    Parameters
    ----------
    xpos : [x1, x2] or scalar
        For a *horizontal* bar: [left, right] as fractions of the axes width.
        For a *vertical* bar: x-centre fraction.
    ypos : scalar or [y1, y2]
        For horizontal: y-centre fraction of the axes height.
        For vertical: [bottom, top] fractions.
    data : 2-D array-like
        The plotted data — used to determine which levels are actually present
        when ``levels_mode='match'``.
    levels : 1-D array-like
        Contour/colour levels (same array passed to m_contourf / caxis).
    colormap : ndarray (n×3) | matplotlib Colormap | None
        Colourmap to use.  If None, reads from the most recent plotted artist
        in the current axes.
    caxis : (vmin, vmax) or None
        Colour axis limits.  If None, reads from the most recent plotted
        artist; falls back to (levels[0], levels[-1]).
    axfrac : float
        Thickness of the colourbar as a fraction of the relevant axis
        dimension (default 0.03).
    endpiece : bool
        If True (default), draw triangular caps when data extends beyond
        the plotted levels.
    levels_mode : {'set', 'match'}
        'set'   — show all supplied levels.
        'match' — subset to levels actually spanned by the data.
    edgecolor : str or None
        Edge colour between colour bands.  None keeps the default ('k');
        pass 'none' to suppress edges.
    fontsize : float or None
        Tick-label font size.  None uses axes default.
    discrete : bool or None
        Whether to draw distinct colour bands (True) or a continuous ramp
        (False).  None (default) infers it from the most recently plotted
        artist: contour sets get bands, images and meshes get a ramp.  Pass an
        explicit value when the bar does not belong to the last artist drawn.
    **kwargs
        Additional keyword arguments forwarded to the colourbar axes (e.g.
        'xticks', 'xticklabels').

    Returns
    -------
    cbar_ax : matplotlib.axes.Axes
        The newly created colourbar axes.
    cb : matplotlib.colorbar.Colorbar
        The colourbar object.
    """
    parent_ax = plt.gca()
    data = np.asarray(data, dtype=float)
    levels = np.asarray(levels, dtype=float)

    # ------------------------------------------------------------------
    # Determine which levels to display
    # ------------------------------------------------------------------
    if levels_mode == 'match':
        data_min = np.nanmin(data)
        data_max = np.nanmax(data)
        mask = (levels >= data_min) & (levels <= data_max)
        clevel = levels[mask]
        if len(clevel) < 2:
            # Fallback: use the full range
            clevel = levels
    else:
        clevel = levels

    # ------------------------------------------------------------------
    # Determine orientation
    # ------------------------------------------------------------------
    xpos = np.atleast_1d(np.asarray(xpos, dtype=float))
    ypos = np.atleast_1d(np.asarray(ypos, dtype=float))

    horiz = len(xpos) == 2 and len(ypos) == 1

    # ------------------------------------------------------------------
    # Compute colourbar axes rect in figure coordinates
    # ------------------------------------------------------------------
    ax_pos = parent_ax.get_position()

    if horiz:
        cx0 = ax_pos.x0 + float(xpos[0]) * ax_pos.width
        cx1 = ax_pos.x0 + float(xpos[1]) * ax_pos.width
        yc = float(ypos[0])
        cy0 = ax_pos.y0 + (yc - axfrac / 2.0) * ax_pos.height
        cy_h = axfrac * ax_pos.height
        cbar_rect = [cx0, cy0, cx1 - cx0, cy_h]
        orientation = 'horizontal'
    else:
        xc = float(xpos[0])
        yp0, yp1 = float(ypos[0]), float(ypos[1])
        cx0_v = ax_pos.x0 + (xc - axfrac / 2.0) * ax_pos.width
        cbar_rect = [
            cx0_v,
            ax_pos.y0 + yp0 * ax_pos.height,
            axfrac * ax_pos.width,
            (yp1 - yp0) * ax_pos.height,
        ]
        orientation = 'vertical'

    # ------------------------------------------------------------------
    # Remove any pre-existing colourbar from this parent axes
    # ------------------------------------------------------------------
    _old = getattr(parent_ax, '_py_m_map_cbar_ax', None)
    if _old is not None:
        try:
            _old.remove()
        except Exception:
            pass

    fig = parent_ax.figure
    cbar_ax = fig.add_axes(cbar_rect)
    parent_ax._py_m_map_cbar_ax = cbar_ax  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Resolve colourmap
    # ------------------------------------------------------------------
    colour_src = _colour_source(parent_ax)

    if colormap is None:
        if colour_src is not None:
            colormap = colour_src.get_cmap()
        else:
            colormap = plt.get_cmap('viridis')

    if isinstance(colormap, np.ndarray):
        listed = ListedColormap(colormap)
    else:
        listed = colormap  # already a Colormap

    # ------------------------------------------------------------------
    # Resolve colour axis
    # ------------------------------------------------------------------
    if caxis is None:
        if colour_src is not None:
            caxis = colour_src.get_clim()
        else:
            caxis = (float(clevel[0]), float(clevel[-1]))

    norm = Normalize(vmin=caxis[0], vmax=caxis[1])

    # ------------------------------------------------------------------
    # Determine extend (end-piece triangles)
    # ------------------------------------------------------------------
    if extend is not None:
        pass  # caller supplied an explicit value — honour it
    elif endpiece:
        data_min = np.nanmin(data)
        data_max = np.nanmax(data)
        below = data_min < float(clevel[0])
        above = data_max > float(clevel[-1])
        if below and above:
            extend = 'both'
        elif below:
            extend = 'min'
        elif above:
            extend = 'max'
        else:
            extend = 'neither'
    else:
        extend = 'neither'

    # ------------------------------------------------------------------
    # Draw using a ScalarMappable + fig.colorbar
    # ------------------------------------------------------------------
    from matplotlib.cm import ScalarMappable
    sm = ScalarMappable(cmap=listed, norm=norm)
    sm.set_array([])

    # Decide between discrete bands and a continuous ramp.  This must match what
    # was actually plotted, which takes both the artist and the colormap:
    #
    #  * A contourf draws a fixed set of bands whatever its colormap, so its bar
    #    must show those bands.  Judging by colour count alone gets this wrong —
    #    contourf with a smooth 256-colour map still draws len(levels)-1 bands.
    #  * An image or mesh (m_etopo2, m_shadedrelief, m_image, m_pcolor) shows
    #    bands only if the colormap itself is a short list of colours.  With a
    #    smooth map it is a gradient, and forcing boundaries= on it would invent
    #    bands the figure does not contain.
    try:
        n_cmap_colors = listed.N
    except AttributeError:
        n_cmap_colors = 256

    if discrete is None:
        # Same artist the colormap and colour limits were taken from above.
        if isinstance(colour_src, ContourSet):
            discrete = len(clevel) <= 50
        else:
            discrete = (n_cmap_colors <= 50) and (len(clevel) <= 50)
    render_continuous = not discrete

    if render_continuous:
        cb = fig.colorbar(
            sm,
            cax=cbar_ax,
            orientation=orientation,
            extend=extend,
        )
        if len(clevel) <= 50:
            # Use the supplied levels as tick positions
            tks = clevel
            if len(tks) > 6:
                stride = max(1, -(-len(tks) // 6))  # ceiling division
                tks = tks[::stride]
            cb.set_ticks(tks)
        else:
            nice_ticks = _nice_cbar_ticks(float(clevel[0]), float(clevel[-1]), target=6)
            cb.set_ticks(nice_ticks)
    else:
        # Discrete bands with proportional widths so the colorbar axis is linear.
        # BoundaryNorm maps band i to color index i; spacing='proportional' sizes
        # each band in proportion to its actual data interval.
        n_bands = len(clevel) - 1
        # BoundaryNorm emits colour *indices* 0…n_bands-1 rather than fractions.
        # A colormap built for these bands already holds one entry per band (plus
        # up to two more for the extend arrows), and those indices address it
        # directly — this is what contourf hands us, and it must be left alone.
        # A genuinely continuous map has to be resampled first: indexing a 128-
        # or 256-entry lut with 0…n_bands-1 would paint every band from its first
        # few colours, turning a topographic bar uniformly deep-blue.
        band_cmap = listed
        n_src = int(getattr(listed, 'N', n_bands))
        if n_bands > 0 and n_src > n_bands + 2:
            sampled = listed(np.linspace(0.0, 1.0, n_bands))
            if np.ptp(sampled[:, :3]) > 0:  # refuse a degenerate resample
                band_cmap = ListedColormap(sampled)
                # Carry the out-of-range colours so extend arrows still match.
                band_cmap.set_over(listed.get_over())
                band_cmap.set_under(listed.get_under())
                band_cmap.set_bad(listed.get_bad())
        bnorm = BoundaryNorm(clevel, ncolors=n_bands, clip=True)
        sm_disc = ScalarMappable(cmap=band_cmap, norm=bnorm)
        sm_disc.set_array([])
        cb = fig.colorbar(
            sm_disc,
            cax=cbar_ax,
            orientation=orientation,
            extend=extend,
            spacing='proportional',
            ticks=clevel,
            drawedges=True,
        )
        # Reduce tick density for readability
        if len(clevel) > 6:
            stride = max(1, -(-len(clevel) // 6))  # ceiling division
            cb.set_ticks(clevel[::stride])

    # Apply edge colour to inter-band dividers only (not the outer box frame).
    # In MATLAB m_contfbar, 'edgecolor','none' suppresses band edges but the
    # colourbar box is always drawn.
    if edgecolor is not None:
        if hasattr(cb, 'dividers'):
            cb.dividers.set_color(edgecolor)

    # Mirror MATLAB's m_contfbar: when the bar is in the upper half of the
    # axes (ypos > 0.5), place tick labels ABOVE the bar.
    if horiz and float(ypos[0]) > 0.5:
        cbar_ax.xaxis.set_ticks_position('top')
        cbar_ax.xaxis.set_label_position('top')

    # Font size — default to 8pt for a thin colourbar; honour explicit override
    fs = fontsize if fontsize is not None else 8
    cb.ax.tick_params(labelsize=fs, direction='out', length=3)

    # ------------------------------------------------------------------
    # Return focus to the parent axes
    # ------------------------------------------------------------------
    plt.sca(parent_ax)

    return cbar_ax, cb
