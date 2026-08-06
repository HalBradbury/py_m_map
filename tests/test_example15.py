"""
Test / reference output for Example 15 — Stepped jet colormap with m_pcolor.

Mirrors m_demo.m / map.html example 15: global pcolor plot of TEOS-10
Absolute Salinity Anomaly (delta-SA) at 3000 dbar on a Pacific-centred
Robinson projection, with a stepped jet colormap.

Requires: gsw (pip install gsw)
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import py_m_map as mm

try:
    import gsw
    _HAS_GSW = True
except ImportError:
    _HAS_GSW = False

OUTPUT_DIR = Path(__file__).parent / 'outputs'


def test_example15():
    OUTPUT_DIR.mkdir(exist_ok=True)

    if _HAS_GSW:
        # TEOS-10 delta-SA atlas at 3000 dbar, global 1° grid (0:360 × -86:89)
        lons_v = np.arange(0, 361, dtype=float)
        lats_v = np.arange(-86, 90, dtype=float)
        LG, LT = np.meshgrid(lons_v, lats_v)
        dSA = gsw.deltaSA_atlas(3000 * np.ones(LG.shape), LG, LT)

        # Rearrange to Pacific-centred: lon cut at 30°E → columns run [31..360, 0..29]
        # Starting at 31° keeps the cut meridian (30°→x_max) off the left edge,
        # preventing jump detection from NaN'ing the leftmost data columns.
        # Stopping at 29° (not 30°) keeps the rightmost column inside x_max so
        # pcolormesh shading='auto' doesn't extend the last cell beyond the boundary.
        ind = list(range(31, 361)) + list(range(0, 30))
        dSA = dSA[:, ind]
        LT_r = LT[:, ind]
        LG_r = LG[:, ind].copy()
        LG_r[LG_r > 30] -= 360   # remap (31, 360] → (-329, 0]

        data = dSA * 1000         # g/kg → mg/kg
        lon_data, lat_data = LG_r, LT_r
        cbar_label = r'$\delta S_A$ (mg kg$^{-1}$)'
        clim = (0, 30)
    else:
        # Fallback: synthetic field if gsw is unavailable
        lons = np.arange(-180, 181, dtype=float)
        lats = np.arange(-80, 81, dtype=float)
        LG, LT = np.meshgrid(lons, lats)
        data = np.sin(np.radians(LT)) * np.cos(np.radians(LG * 0.5))
        lon_data, lat_data = LG, LT
        cbar_label = 'Synthetic field (a.u.)'
        clim = None

    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.reset_state()
    if _HAS_GSW:
        mm.m_proj('robinson', lon=[-330, 30], lat=[-90, 90])
    else:
        mm.m_proj('miller', lat=[-77, 77])

    h = mm.m_pcolor(lon_data, lat_data, data)
    mm.m_coast('patch', color=[0.7, 0.7, 0.7], edgecolor='none')
    mm.m_grid(tickdir='out', linewidth=2)

    cmap = mm.m_colmap('jet', 'step')
    h.set_cmap(cmap)
    if clim is not None:
        h.set_clim(*clim)

    cb = fig.colorbar(h, ax=ax, orientation='horizontal', pad=0.08, fraction=0.04)
    cb.set_label(cbar_label)

    fig.set_facecolor('white')
    out = OUTPUT_DIR / 'example15.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example15()
