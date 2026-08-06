"""
Test / reference output for Example 15 (inverse) — land-coloured, gray ocean,
three projections stacked in a single column.

Robinson (Pacific-centred), Mollweide, and Miller each show the same sin(lat)
field restricted to land only.  Ocean is filled with steel-blue gray via
m_grid's backcolor parameter.  Panel C (Miller) has a ruler box border.
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

OCEAN_GRAY = [0.45, 0.60, 0.75]


# ---------------------------------------------------------------------------
# Data grids
# ---------------------------------------------------------------------------

def _pacific_grid():
    """1° grid remapped to Pacific-centred [−330, 30] range."""
    lons_v = np.arange(0, 361, dtype=float)
    lats_v = np.arange(-86, 90, dtype=float)
    LG, LT = np.meshgrid(lons_v, lats_v)
    data_raw = np.sin(np.radians(LT))
    ind = list(range(31, 361)) + list(range(0, 30))
    LG_r = LG[:, ind].copy()
    LG_r[LG_r > 30] -= 360
    return LG_r, LT[:, ind], data_raw[:, ind]


def _standard_grid(lat_max=89):
    """1° grid on [−180, 180] × [−86, lat_max]."""
    LG, LT = np.meshgrid(np.arange(-180, 181, dtype=float),
                          np.arange(-86, lat_max + 1, dtype=float))
    return LG, LT, np.sin(np.radians(LT))


# ---------------------------------------------------------------------------
# Panel configuration
# ---------------------------------------------------------------------------

_PANELS = [
    dict(proj='robinson', proj_kw=dict(lon=[-330, 30], lat=[-90, 90]),
         grid_fn=_pacific_grid),
    dict(proj='mollweide', proj_kw=dict(lon=[-180, 180], lat=[-90, 90]),
         grid_fn=_standard_grid),
    dict(proj='miller',    proj_kw=dict(lat=[-77, 77]),
         grid_fn=lambda: _standard_grid(lat_max=76)),
]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def test_example15_inverse():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig, axes = plt.subplots(3, 1, figsize=(10, 15), facecolor='white')

    h_last = None
    for ax, panel, letter in zip(axes, _PANELS, 'ABC'):
        ax.set_facecolor('white')
        plt.sca(ax)

        mm.reset_state()
        mm.m_proj(panel['proj'], **panel['proj_kw'])

        LG_r, LT_r, data = panel['grid_fn']()
        land_mask = mm.m_landmask(LG_r, LT_r)
        data_land = data.copy()
        data_land[~land_mask] = np.nan

        no_xlab = (letter == 'B')
        ruler = (letter == 'C')
        h = mm.m_pcolor(LG_r, LT_r, data_land)
        mm.m_coast('line', color='k', linewidth=0.4)
        mm.m_grid(tickdir='out', linewidth=2, backcolor=OCEAN_GRAY,
                  xticklabels=(False if no_xlab else None),
                  box=('fancy' if ruler else None),
                  boxstyle=('line' if ruler else None))

        cmap = mm.m_colmap('jet', 'step')
        h.set_cmap(cmap)
        h.set_clim(-1, 1)

        ax.text(0.01, 0.97, letter, transform=ax.transAxes,
                fontweight='bold', va='top', ha='left')

        h_last = h

    cb = fig.colorbar(h_last, ax=axes.tolist(), orientation='horizontal',
                      pad=0.06, fraction=0.02, shrink=0.55)
    cb.set_label(r'$\sin(\phi)$')

    fig.set_facecolor('white')
    out = OUTPUT_DIR / 'example15_inverse.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example15_inverse()
