"""
Test / reference output for Example 9 — GSHHS coastlines at multiple scales.
Mirrors m_demo.m case 9: Nova Scotia zoom sequence using Albers Equal-Area.
Six panels at progressively finer zoom levels, each with a resolution label,
geographic scale bar, and opaque white background.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import py_m_map as mm


OUTPUT_DIR = Path(__file__).parent / 'outputs'


def _add_label(ax, text: str, fontsize: int = 7) -> None:
    ax.text(0.03, 0.97, text,
            transform=ax.transAxes, fontsize=fontsize,
            va='top', ha='left', zorder=20,
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.85, pad=1.5))


def _white_bg(ax) -> None:
    """Draw opaque white fill shaped exactly like the current map frame polygon.

    Must be called after mm.m_proj() so the projection state is available.
    The fill is drawn at zorder=-1 so it sits behind all map content but
    covers any lower-zorder axes content that falls within the map frame.
    """
    state = mm.get_state()
    if state.proj is None:
        return
    n = 200
    lon_min, lon_max = state.lon_limits
    lat_min, lat_max = state.lat_limits
    # Trace the geographic boundary clockwise in (lon, lat)
    lons = np.concatenate([
        np.linspace(lon_min, lon_max, n),  # bottom: left → right
        np.full(n, lon_max),               # right:  bottom → top
        np.linspace(lon_max, lon_min, n),  # top:    right → left
        np.full(n, lon_min),               # left:   top → bottom
    ])
    lats = np.concatenate([
        np.full(n, lat_min),               # bottom
        np.linspace(lat_min, lat_max, n),  # right
        np.full(n, lat_max),               # top
        np.linspace(lat_max, lat_min, n),  # left
    ])
    x, y = mm.m_ll2xy(lons, lats)
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ax.fill(x, y, facecolor='white', edgecolor='none', zorder=-1)


def test_example9():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig = plt.figure(figsize=(11, 8.5), facecolor='white')

    # --- Panel 1: continental overview — Natural Earth ---
    ax1 = fig.add_axes([0.35, 0.60, 0.37, 0.37])
    ax1.set_facecolor('white')
    ax1.set_zorder(1)
    plt.sca(ax1)
    mm.reset_state()
    mm.m_proj('albers', lon=[-90, -50], lat=[40, 60])
    mm.m_coast('patch', [0, 1, 0])
    mm.m_grid(linestyle='none', linewidth=2, tickdir='out',
               xaxislocation='top', yaxislocation='right', fontsize=6)
    mm.m_ruler([0.30, 0.70], 0.90, nbar=4, fontsize=6)
    _add_label(ax1, 'Natural Earth (auto)')

    # --- Panel 2: GSHHS crude (~480 km) ---
    ax2 = fig.add_axes([0.09, 0.50, 0.37, 0.37])
    ax2.set_facecolor('none')
    ax2.set_zorder(2)
    plt.sca(ax2)
    mm.reset_state()
    mm.m_proj('albers', lon=[-80, -55], lat=[40, 54])
    _white_bg(ax2)
    mm.m_gshhs_c('patch', [0.2, 0.8, 0.2])
    mm.m_grid(linestyle='none', linewidth=2, tickdir='out',
               xaxislocation='top', fontsize=6)
    mm.m_ruler([0.55, 0.90], 0.90, nbar=4, fontsize=6)
    _add_label(ax2, 'GSHHS crude (c)')

    # --- Panel 3: GSHHS low (~108 km) ---
    ax3 = fig.add_axes([0.13, 0.20, 0.37, 0.37])
    ax3.set_facecolor('none')
    ax3.set_zorder(3)
    plt.sca(ax3)
    mm.reset_state()
    mm.m_proj('albers', lon=[-67, -58], lat=[43, 48])
    _white_bg(ax3)
    mm.m_gshhs_l('patch', [0.4, 0.6, 0.4])
    mm.m_grid(linestyle='none', linewidth=2, tickdir='out', fontsize=6)
    mm.m_ruler([0.55, 0.90], 0.90, nbar=4, fontsize=6)
    _add_label(ax3, 'GSHHS low (l)')

    # --- Panel 4: GSHHS intermediate (~23 km) ---
    ax4 = fig.add_axes([0.35, 0.05, 0.37, 0.37])
    ax4.set_facecolor('none')
    ax4.set_zorder(4)
    plt.sca(ax4)
    mm.reset_state()
    mm.m_proj('albers', lon=[-64.5, -62], lat=[45.8, 47.2])
    _white_bg(ax4)
    mm.m_gshhs_i('patch', [0.5, 0.6, 0.5])
    mm.m_grid(linestyle='none', linewidth=2, tickdir='out',
               yaxislocation='right', fontsize=6)
    mm.m_ruler([0.55, 0.90], 0.10, nbar=4, fontsize=6)
    _add_label(ax4, 'GSHHS intermediate (i)')

    # --- Panel 5: GSHHS high (~0.2 km) ---
    ax5 = fig.add_axes([0.50, 0.10, 0.37, 0.37])
    ax5.set_facecolor('none')
    ax5.set_zorder(5)
    plt.sca(ax5)
    mm.reset_state()
    mm.m_proj('albers', lon=[-64.2, -63.7], lat=[46.375, 46.6])
    _white_bg(ax5)
    mm.m_gshhs_h('patch', [0.6, 0.7, 0.6])
    mm.m_grid(linestyle='none', linewidth=2, tickdir='out',
               xaxislocation='top', yaxislocation='right', fontsize=6)
    mm.m_ruler([0.55, 0.90], 0.10, nbar=4, fontsize=6)
    _add_label(ax5, 'GSHHS high (h)')

    # --- Panel 6: GSHHS full (~0.04 km) ---
    ax6 = fig.add_axes([0.55, 0.35, 0.37, 0.37])
    ax6.set_facecolor('none')
    ax6.set_zorder(6)
    plt.sca(ax6)
    mm.reset_state()
    mm.m_proj('albers', lon=[-63.97, -63.77], lat=[46.55, 46.65])
    _white_bg(ax6)
    mm.m_gshhs_f('patch', [0.7, 0.9, 0.7])
    mm.m_grid(linestyle='none', linewidth=2, tickdir='out',
               xaxislocation='top', yaxislocation='right', fontsize=6)
    mm.m_ruler([0.55, 0.90], 0.10, nbar=4, fontsize=6)
    _add_label(ax6, 'GSHHS full (f)')

    out = OUTPUT_DIR / 'example9.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example9()
