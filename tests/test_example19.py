"""
Example 19 — Wind Roses, Strait of Georgia, oblique Mercator projection.

Mirrors map.html Example 19 (Pawlowicz).  Real station data are not
available; synthetic wind records are used instead.

MATLAB reference:
    m_proj('oblique','lon',[-125.3 -122.6],'lat',[50.1 48.6],'dir','vert','aspect',0.45)
    m_windrose({lon},{lat},{wdir},{wspd},'size',.17,'nspeed',levels,'alpha',1)
    colormap(m_colmap('jet')); caxis([0 24]);
    axb = m_contfbar(.8,[.6 .9],levels,levels);
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

# Strait of Georgia stations — positions within the map domain
STATIONS_LON = [-124.4, -124.1, -123.9, -123.7, -123.5, -123.2,
                -124.2, -123.8, -123.5, -124.0]
STATIONS_LAT = [49.2,   49.5,   49.7,   49.9,   49.6,   49.3,
                49.85,  49.15,  49.95,  49.5]


def _synthetic_wind(lon, lat, seed, n=500):
    """
    Generate realistic-looking synthetic wind directions and speeds for one
    Strait of Georgia station.

    Northern stations are biased toward NW–SE channel winds (dominant ~315°);
    southern stations have a broader mix with a secondary SE mode (~135°).
    """
    rng = np.random.default_rng(seed)

    # Fraction of observations from the NW-quadrant mode
    frac_nw = np.clip(0.45 + 0.6 * (lat - 49.5) / 0.8, 0.15, 0.85)
    n_nw = int(n * frac_nw)
    n_se = n - n_nw

    # Northwest winds: direction ≈ 310–340°, moderate–strong
    dir_nw = rng.normal(320, 22, n_nw) % 360
    spd_nw = rng.gamma(2.5, 3.5, n_nw) + 1.5

    # Southeast / southerly return flow: direction ≈ 120–160°, lighter
    dir_se = rng.normal(145, 28, n_se) % 360
    spd_se = rng.gamma(1.8, 2.8, n_se) + 0.5

    dirs = np.concatenate([dir_nw, dir_se]) % 360
    spds = np.clip(np.concatenate([spd_nw, spd_se]), 0.0, 25.0)
    return dirs, spds


def test_example19():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    levels = np.arange(0, 25, 4, dtype=float)   # [0, 4, 8, 12, 16, 20, 24]

    thets_list = []
    spds_list  = []
    for i, (lo, la) in enumerate(zip(STATIONS_LON, STATIONS_LAT)):
        dirs, spds = _synthetic_wind(lo, la, seed=i, n=600)
        thets_list.append(dirs)
        spds_list.append(spds)

    fig, ax = plt.subplots(figsize=(7, 11), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('oblique', lon=[-125.3, -122.6], lat=[50.1, 48.6], aspect=0.45)
    mm.m_coast('patch', color=[0.85, 0.85, 0.85], edgecolor='none')

    pcs = mm.m_windrose(
        STATIONS_LON, STATIONS_LAT,
        thets_list, spds_list,
        nspeeds=levels,
        ndirs=16,
        size=0.17,
        alpha=1.0,
    )

    # Apply jet colormap and colour limits to all roses
    cmap = mm.m_colmap('jet')
    for pc in pcs:
        if pc is not None:
            pc.set_cmap(cmap)
            pc.set_clim(0, 24)

    mm.m_grid(tickdir='out', linestyle='none')

    cbar_ax, cb = mm.m_contfbar(
        1.07, [0.1, 0.9], levels, levels,
        colormap=cmap, caxis=(0, 24),
    )
    cbar_ax.set_ylabel('Wind speed (m s$^{-1}$)')

    out = OUTPUT_DIR / 'example19.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example19()
