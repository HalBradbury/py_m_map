"""
Fancy arrow / quiver patches on a map.

m_vec — ported from m_vec.m (Eric Firing, U. Hawaii; R. Pawlowicz)

Algorithm
---------
Each arrow is built as a 7-vertex (or more, for curved arrows) polygon in a
normalised frame where the arrow points along +x with its tail at the origin.
The polygon is then rotated by the arrow's local bearing in map coordinates
(computed by projecting two nearby geographic points) and translated to the
projected tail position.  Drawing uses matplotlib Polygon patches; a
PatchCollection is used for colour-mapped arrows.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.collections as mcollections
from .projection import m_ll2xy, m_xy2ll
from ._state import get_state


def m_vec(
    scale: float,
    lon,
    lat,
    u,
    v,
    color=None,
    *,
    headangle: float = 40.0,
    headlength: float = 5.0,
    headwidth: float | None = None,
    headstyle: int = 2,
    shaftwidth: float = 1.0,
    centered: str | bool = 'no',
    key: str = '',
    edgeclip: bool | str = False,
    curvature: float = 0.0,
    **patch_kwargs,
):
    """
    Draw fancy arrows on the current map.

    Parameters
    ----------
    scale : float
        Data units per inch.  e.g. scale=100 means a vector of magnitude 100
        data units draws an arrow 1 inch long.
    lon, lat : array-like
        Geographic position of each arrow tail (decimal degrees).
    u, v : array-like
        Eastward and northward components (same units as scale).
    color : str, (3,) array, (N,) array, or None
        Arrow colour.  None or omitted → black.
        A 1-D array of length N → colour-mapped via the current colormap.
    headangle : float
        Half-angle of the arrowhead tip in degrees (default 40).
    headlength : float
        Arrowhead length in points (default 5).
    headwidth : float or None
        Arrowhead half-width in points.  Default: computed from headangle.
    headstyle : int (1–4)
        1 — flush head (no extra head protrusion)
        2 — standard (default)
        3 — concave back
        4 — half-concave
    shaftwidth : float
        Shaft half-width in points (default 1).
    centered : str or bool
        'no' (default) — tail at (lon, lat).
        'yes' / True   — arrow centred on (lon, lat).
        'tail'         — arrowhead at (lon, lat).
    key : str
        If non-empty, draw a horizontal key arrow with this label.
    edgeclip : bool or 'on'/'off'
        Clip arrows to the map boundary (default False).
    curvature : float
        Arc angle in degrees for a curved arrow shaft (default 0 = straight).
    **patch_kwargs
        Passed to all Polygon patches (e.g. EdgeColor, linewidth, zorder).

    Returns
    -------
    hp : list of Polygon patches (or a PatchCollection for colour-mapped arrows)
    ht : text Artist if key != '', else None
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    lon = np.atleast_1d(np.asarray(lon, dtype=float)).ravel()
    lat = np.atleast_1d(np.asarray(lat, dtype=float)).ravel()
    u   = np.atleast_1d(np.asarray(u,   dtype=float)).ravel()
    v   = np.atleast_1d(np.asarray(v,   dtype=float)).ravel()

    # Broadcast lon/lat to match u/v length
    if lon.size == 1 and u.size > 1:
        lon = np.full_like(u, lon[0])
        lat = np.full_like(u, lat[0])

    nvec = len(u)

    # ------------------------------------------------------------------
    # Resolve colour
    # ------------------------------------------------------------------
    use_cmap = False
    cdata = None
    if color is None:
        facecolor = 'k'
        edgecolor_default = 'k'
    elif isinstance(color, str):
        facecolor = color
        edgecolor_default = color
    elif np.ndim(color) == 1 and len(color) == 3 and np.max(color) <= 1.0:
        facecolor = tuple(color)
        edgecolor_default = tuple(color)
    elif np.ndim(color) == 1 and len(color) == nvec:
        use_cmap = True
        cdata = np.asarray(color, dtype=float)
        facecolor = 'k'
        edgecolor_default = 'none'
    else:
        facecolor = color
        edgecolor_default = 'none'

    # ------------------------------------------------------------------
    # Axes scale: data units per inch
    # ------------------------------------------------------------------
    ax = plt.gca()
    fig = ax.figure
    fig_w, fig_h = fig.get_size_inches()
    ax_pos = ax.get_position()
    ax_w_in = ax_pos.width  * fig_w
    ax_h_in = ax_pos.height * fig_h

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    scX = (xlim[1] - xlim[0]) / ax_w_in if ax_w_in > 0 else 1.0
    scY = (ylim[1] - ylim[0]) / ax_h_in if ax_h_in > 0 else 1.0
    sc = max(scX, scY)  # data units per inch

    # Arrow dimensions in data units (input params are in points; 1 in = 72 pt)
    HL0 = headlength / 72.0 * sc
    if headwidth is None and headangle > 0 and headangle < 170:
        HW0 = HL0 * np.tan(np.radians(headangle))
    else:
        HW0 = (headwidth or 0.0) / 72.0 * sc
    HW0 = max(HW0, shaftwidth / 72.0 * sc)
    W0  = shaftwidth / 72.0 * sc

    # Head style → hval (how far back the head notch is)
    hval_map = {1: 0.0, 2: 1.0, 3: 2.0, 4: 0.5}
    hval = hval_map.get(headstyle, 1.0)

    # Arrow lengths in data units
    uvmag = np.hypot(u, v)
    uvmag_safe = np.where(uvmag < 1e-10 * np.max(uvmag + 1e-30), np.nan, uvmag)
    L = uvmag / scale * sc  # data units

    # ------------------------------------------------------------------
    # Centring offset along shaft axis
    # ------------------------------------------------------------------
    def _xzero(l):
        c = str(centered).lower()
        if c in ('yes', 'true', '1'):
            return -l / 2.0
        elif c == 'tail':
            return -l
        return 0.0

    # ------------------------------------------------------------------
    # Project tail positions and compute bearing angles in map coords
    # ------------------------------------------------------------------
    clip_mode = 'on' if not key else 'off'
    xs, ys = m_ll2xy(lon, lat, clip=clip_mode)
    xs = np.asarray(xs, dtype=float)
    ys = np.asarray(ys, dtype=float)

    eps = 1e-5
    u_n = u / uvmag_safe     # unit east (NaN for zero vectors)
    v_n = v / uvmag_safe     # unit north

    lon2 = lon + eps * u_n
    lat2 = lat + eps * v_n * np.cos(np.radians(lat))
    xsp, ysp = m_ll2xy(np.stack([lon, lon2], axis=1),
                       np.stack([lat, lat2], axis=1), clip='off')
    xsp = np.asarray(xsp, dtype=float)
    ysp = np.asarray(ysp, dtype=float)
    Ang = np.angle((xsp[:, 1] - xsp[:, 0]) + 1j * (ysp[:, 1] - ysp[:, 0]))

    if key:
        Ang[:] = 0.0  # key arrow is always horizontal

    # ------------------------------------------------------------------
    # Build polygon vertices for each arrow
    # ------------------------------------------------------------------
    patches = []
    cdata_out = []

    for k in range(nvec):
        if not np.isfinite(xs[k]) or not np.isfinite(ys[k]):
            continue
        if not np.isfinite(uvmag_safe[k]):
            continue   # zero-length vector

        Lk  = L[k]
        HLk = HL0
        HWk = HW0
        Wk  = W0

        if HLk == 0:
            # No head
            HWk = Wk
            HLk = 0.0
        elif Lk < HLk:
            # Very short arrow: just a scaled head, no shaft
            Wk  = 0.0
            HLk = Lk
            HWk = HLk * (HW0 / HL0) if HL0 > 0 else HLk

        xz = _xzero(Lk)

        if abs(curvature) < 1e-6:
            # Straight arrow — 7 vertices
            vx = np.array([
                xz,
                xz + Lk - HLk * hval,
                xz + Lk - HLk,
                xz + Lk,
                xz + Lk - HLk,
                xz + Lk - HLk * hval,
                xz,
            ])
            vy = np.array([Wk/2, Wk/2, HWk/2, 0.0, -HWk/2, -Wk/2, -Wk/2])
        else:
            # Curved arrow — shaft follows a circular arc
            nc = int(np.ceil(abs(curvature)))  # extra arc points
            rad = Lk / (abs(curvature) * np.pi / 180.0)
            n_arc = 2 + nc
            arc_top = np.linspace(xz, xz + Lk - HLk * hval, n_arc)
            arc_bot = arc_top[::-1]
            vx = np.concatenate([arc_top, [xz + Lk - HLk, xz + Lk, xz + Lk - HLk],
                                  arc_bot])
            vy = np.concatenate([np.full(n_arc, Wk/2),
                                  [HWk/2, 0.0, -HWk/2],
                                  np.full(n_arc, -Wk/2)])
            # Convert to circular arc coordinates
            th = vx / rad
            r  = vy + rad
            vx_c = r * np.sin(th)
            vy_c = r * np.cos(th) - rad  # translate so tail is at origin
            if curvature < 0:
                vx_c, vy_c = vx_c, -vy_c
            vx = vx_c
            vy = vy_c

        # Rotate and translate
        z = (vx + 1j * vy) * np.exp(1j * Ang[k])
        px = xs[k] + np.real(z)
        py = ys[k] + np.imag(z)
        verts = np.column_stack([px, py])

        skip_patch = False
        if edgeclip in (True, 'on'):
            _ec_state = get_state()
            if _ec_state.projection_type == 'circular':
                from shapely.geometry import Polygon as SPoly, Point
                from shapely.validation import make_valid
                R_clip = float(_ec_state.x_limits[1])
                disk = Point(0.0, 0.0).buffer(R_clip, resolution=128)
                try:
                    arrow_poly = SPoly(verts)
                    if not arrow_poly.is_valid:
                        arrow_poly = make_valid(arrow_poly)
                    clipped = arrow_poly.intersection(disk)
                    if clipped.is_empty:
                        skip_patch = True
                    elif clipped.geom_type == 'Polygon':
                        cx, cy = clipped.exterior.xy
                        verts = np.column_stack([np.array(cx), np.array(cy)])
                    elif clipped.geom_type == 'MultiPolygon':
                        largest = max(clipped.geoms, key=lambda p: p.area)
                        cx, cy = largest.exterior.xy
                        verts = np.column_stack([np.array(cx), np.array(cy)])
                except Exception:
                    pass
            else:
                # Rectangular/conic: re-project vertices to apply map clipping
                vlon_c, vlat_c = m_xy2ll(px, py)
                px2, py2 = m_ll2xy(vlon_c, vlat_c, clip='patch')
                px2, py2 = np.asarray(px2, float), np.asarray(py2, float)
                ok = np.isfinite(px2) & np.isfinite(py2)
                verts = np.column_stack([np.where(ok, px2, px),
                                         np.where(ok, py2, py)])

        if not skip_patch:
            patches.append(verts)
            if use_cmap:
                cdata_out.append(cdata[k])

    # ------------------------------------------------------------------
    # Draw patches
    # ------------------------------------------------------------------
    result_patches = []
    ht = None

    ec = patch_kwargs.pop('edgecolor', patch_kwargs.pop('EdgeColor', edgecolor_default))
    lw = patch_kwargs.pop('linewidth',  patch_kwargs.pop('LineWidth', 0.1))

    if use_cmap:
        polys = [mpatches.Polygon(v, closed=True) for v in patches]
        pc = mcollections.PatchCollection(
            polys, cmap=plt.get_cmap(None), clim=ax.get_clim() if hasattr(ax, 'get_clim') else None,
            edgecolors=ec, linewidths=lw, clip_on=False, **patch_kwargs
        )
        pc.set_array(np.array(cdata_out))
        pc.set_clim(*ax.images[0].get_clim() if ax.images else (None, None))
        # Try to pick up the current colormap/clim from any plotted artist
        all_artists = list(ax.collections) + list(ax.images)
        if all_artists:
            try:
                pc.set_cmap(all_artists[0].get_cmap())
                pc.set_clim(*all_artists[0].get_clim())
            except Exception:
                pass
        ax.add_collection(pc)
        result_patches = pc
    else:
        for v in patches:
            p = mpatches.Polygon(
                v, closed=True,
                facecolor=facecolor, edgecolor=ec, linewidth=lw,
                clip_on=False, **patch_kwargs
            )
            ax.add_patch(p)
            result_patches.append(p)

    # ------------------------------------------------------------------
    # Key (legend arrow + label)
    # ------------------------------------------------------------------
    if key and patches:
        verts0 = patches[0]
        x_txt = verts0[:, 0].max()
        y_txt = verts0[:, 1].min() - HW0 * 0.5
        ht = ax.text(
            x_txt, y_txt, key,
            ha='left', va='top', clip_on=False,
            color=facecolor if not use_cmap else 'k',
        )

    return result_patches, ht
