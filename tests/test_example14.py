"""
Test / reference output for Example 14 — "One Ocean" azimuthal equal-area map.

Four panels in a 2×2 grid, all using Lambert azimuthal equal-area centred at
(lon=-95, lat=-46) with radius=156°:
  A — m_coast patch (land red, ocean white)
  B — m_elev contourf using 'blues' + 'gland' colormaps
  C — m_elev image using same colormap
  D — m_elev shadedrelief
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import py_m_map as mm

OUTPUT_DIR = Path(__file__).parent / 'outputs'

_LON_C = -95.0
_LAT_C = -46.0
_RADIUS = 156.0


def _setup_proj():
    mm.reset_state()
    mm.m_proj('azimuthal equal-area', lon=_LON_C, lat=_LAT_C, radius=_RADIUS)


def test_example14():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(12, 12), facecolor='white')

    # --- Panel A: coast patch only ---
    ax = axes[0, 0]
    ax.set_facecolor('white')
    plt.sca(ax)
    _setup_proj()
    mm.m_coast('patch', facecolor=[0.85, 0.3, 0.3], edgecolor='k', linewidth=0.3)
    mm.m_coast('line', color='k', linewidth=0.3)
    mm.m_grid(linewidth=0.5, xticklabels=False, yticklabels=False)
    ax.text(0.01, 0.97, 'A', transform=ax.transAxes, fontweight='bold', va='top', ha='left')

    import matplotlib.colors as mcolors
    import numpy as np

    # Build a combined blues+gland colormap whose boundary sits exactly at 0 m.
    # Data spans roughly -7000 m (ocean) to +5000 m (land), total 12000 m.
    # Allocate colormap entries proportionally so the blues-to-gland join aligns
    # with sea level when vmin=-7000 and vmax=5000.
    _VMIN, _VMAX = -7000.0, 5000.0
    _VCENTER = 0.0
    _N_TOTAL = 256
    _n_blues = round(_N_TOTAL * (_VCENTER - _VMIN) / (_VMAX - _VMIN))
    _n_gland = _N_TOTAL - _n_blues

    cmap_blues = mm.m_colmap('blues', _n_blues)
    cmap_gland = mm.m_colmap('gland', _n_gland)
    cmap_combined = mcolors.ListedColormap(np.vstack([cmap_blues.colors, cmap_gland.colors]))

    # --- Panel B: m_elev contourf (blues = bathymetry colormap) ---
    ax = axes[0, 1]
    ax.set_facecolor('white')
    plt.sca(ax)
    _setup_proj()
    mm.m_elev('contourf', cmap=cmap_combined, vmin=_VMIN, vmax=_VMAX)
    mm.m_coast('line', color='k', linewidth=0.3)
    mm.m_grid(linewidth=0.5, xticklabels=False, yticklabels=False)
    ax.text(0.01, 0.97, 'B', transform=ax.transAxes, fontweight='bold', va='top', ha='left')

    # --- Panel C: m_elev image (same combined colormap) ---
    ax = axes[1, 0]
    ax.set_facecolor('white')
    plt.sca(ax)
    _setup_proj()
    mm.m_elev('image', cmap=cmap_combined, vmin=_VMIN, vmax=_VMAX)
    mm.m_coast('line', color='k', linewidth=0.3)
    mm.m_grid(linewidth=0.5, xticklabels=False, yticklabels=False)
    ax.text(0.01, 0.97, 'C', transform=ax.transAxes, fontweight='bold', va='top', ha='left')

    # --- Panel D: m_elev shadedrelief ---
    ax = axes[1, 1]
    ax.set_facecolor('white')
    plt.sca(ax)
    _setup_proj()
    mm.m_elev('shadedrelief', colormap=cmap_blues)
    mm.m_coast('line', color='k', linewidth=0.3)
    mm.m_grid(linewidth=0.5, xticklabels=False, yticklabels=False)
    ax.text(0.01, 0.97, 'D', transform=ax.transAxes, fontweight='bold', va='top', ha='left')

    fig.set_facecolor('white')
    out = OUTPUT_DIR / 'example14_one_ocean.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example14()
