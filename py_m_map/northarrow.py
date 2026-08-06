"""
Compass rose / north arrow for map plots.

m_northarrow — ported from m_northarrow.m (R. Pawlowicz, Jan 2020)
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from .projection import m_ll2xy
from ._state import get_state


def m_northarrow(lon: float, lat: float, scale: float, *,
                 type: int = 4,
                 aspect: float = 1.0,
                 linewi: float = 1.0,
                 **kwargs) -> list:
    """
    Draw a north arrow or compass rose on the current map.

    Parameters
    ----------
    lon, lat : float
        Geographic position of the arrow centre (decimal degrees).
    scale : float
        Size in degrees of latitude.
    type : int (1–4)
        Arrow design:
          1 — simple black arrow, no stem
          2 — black-and-white half arrow
          3 — 4-point compass rose
          4 — 8-point compass rose (default)
    aspect : float
        >1 makes the shape thinner; <1 makes it fatter.
    linewi : float
        Edge line width (maps to matplotlib ``linewidth``).
    **kwargs
        Forwarded to all Polygon patches (e.g. ``zorder``).

    Returns
    -------
    list of matplotlib.patches.Polygon
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    # Northward direction vector in map coordinates.
    # Project (lon, lat) and (lon, lat+0.01), take the difference × 100
    # to get a unit-ish complex number pointing north.
    x01, y01 = m_ll2xy([lon, lon], [lat, lat + 0.01], clip='off')
    x01 = np.asarray(x01, dtype=float)
    y01 = np.asarray(y01, dtype=float)
    dN = ((x01[1] - x01[0]) + 1j * (y01[1] - y01[0])) * 100.0
    x0, y0 = float(x01[0]), float(y01[0])

    gray = [0.7, 0.7, 0.7]

    # Build template shapes in the normalized complex frame where +real = north.
    # All types produce:
    #   zN  — "N" letter polygon
    #   zab — main rose/arrow shape (will be drawn gray)
    #   zaw — same shape conjugate-mirrored (will be drawn white); None for type 1

    if type == 1:
        za = (1j * np.array([0.1, 0.1, 1.5, 0.0, -1.5, -0.1, -0.1, 0.1]) / aspect
              + np.array([-0.5, 1.0, 0.0, 5.0, 0.0, 1.0, -0.5, -0.5]) - 2.5)
        zN = (1j * np.array([-0.7, -0.7, 0.7, 0.7, 0.7, -0.7, -0.7])
              + np.array([8.0, 6.0, 8.0, 6.0, 8.0, 6.0, 8.0]) - 3.0)
        zN  = zN  / 5.0 * dN * scale
        zab = za  / 5.0 * dN * scale
        zaw = None

    elif type == 2:
        za = (1j * np.array([0.0, 1.5, 0.0, 0.0]) / aspect
              + np.array([1.0, 0.0, 5.0, 1.0]) - 2.5)
        zN = (1j * np.array([-0.7, -0.7, 0.7, 0.7, 0.7, -0.7, -0.7])
              + np.array([8.0, 6.0, 8.0, 6.0, 8.0, 6.0, 8.0]) - 3.0)
        zN  = zN         / 5.0 * dN * scale
        zaw = za          / 5.0 * dN * scale
        zab = np.conj(za) / 5.0 * dN * scale

    elif type == 3:
        za_one = (np.array([0.0, 1.0 / aspect, 6.0, 0.0])
                  + 1j * np.array([0.0, 1.0 / aspect, 0.0, 0.0]))
        za = np.concatenate([za_one, 1j * za_one, -za_one, -1j * za_one])
        zN = (1j * np.array([-0.7, -0.7, 0.7, 0.7, 0.7, -0.7, -0.7])
              + np.array([8.0, 6.0, 8.0, 6.0, 8.0, 6.0, 8.0]))
        zN  = zN          / 12.0 * dN * scale
        zaw = za           / 12.0 * dN * scale
        zab = np.conj(za)  / 12.0 * dN * scale

    else:  # type == 4  (8-point compass rose)
        sfac = 2.0 / aspect
        r1 = sfac * np.cos(np.radians(22.5))
        i1 = sfac * np.sin(np.radians(22.5))
        r2 = sfac * np.cos(np.radians(67.5))
        i2 = sfac * np.sin(np.radians(67.5))
        za_one = (np.array([0.0, r1, 6.0, 0.0, r2, 3.0, 0.0])
                  + 1j * np.array([0.0, i1, 0.0, 0.0, i2, 3.0, 0.0]))
        za = np.concatenate([za_one, 1j * za_one, -za_one, -1j * za_one])
        zN = (1j * np.array([-0.7, -0.7, 0.7, 0.7, 0.7, -0.7, -0.7])
              + np.array([8.0, 6.0, 8.0, 6.0, 8.0, 6.0, 8.0]))
        zN  = zN          / 12.0 * dN * scale
        zaw = za           / 12.0 * dN * scale
        zab = np.conj(za)  / 12.0 * dN * scale

    ax = plt.gca()
    handles = []
    kwargs.setdefault('zorder', 11)
    patch_kw = dict(clip_on=False, **kwargs)
    text_kw = {'clip_on': False, 'zorder': kwargs['zorder']}

    # "N" letter — rendered as text to avoid self-intersection artefacts
    norm = 12.0 if type in (3, 4) else 5.0
    n_ctr_r = (7.0 if type in (3, 4) else 4.0)
    z_n_ctr = n_ctr_r / norm * dN * scale
    n_cx = x0 + np.real(z_n_ctr)
    n_cy = y0 + np.imag(z_n_ctr)
    n_half_h_y = 0.7 / norm * abs(np.imag(dN)) * scale
    fig = ax.get_figure()
    p0 = ax.transData.transform((n_cx, n_cy - n_half_h_y))
    p1 = ax.transData.transform((n_cx, n_cy + n_half_h_y))
    fontsize = max(6.0, abs(p1[1] - p0[1]) * 72.0 / fig.dpi * 1.5)
    hn = ax.text(n_cx, n_cy, 'N', ha='center', va='center',
                 fontsize=fontsize, fontweight='bold', **text_kw)
    handles.append(hn)

    # Main rose — gray fill (conjugate shape)
    vab = np.column_stack([x0 + np.real(zab), y0 + np.imag(zab)])
    h2 = Polygon(vab, closed=True, facecolor=gray, edgecolor='k',
                 linewidth=linewi, **patch_kw)
    ax.add_patch(h2)
    handles.append(h2)

    # Main rose — white fill (original shape); omitted for type 1
    if zaw is not None:
        vaw = np.column_stack([x0 + np.real(zaw), y0 + np.imag(zaw)])
        h3 = Polygon(vaw, closed=True, facecolor='w', edgecolor='k',
                     linewidth=linewi, **patch_kw)
        ax.add_patch(h3)
        handles.append(h3)

    return handles
