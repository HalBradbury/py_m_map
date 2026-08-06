"""
Test / reference output for Example 10 — UTM grid with ship track.
Mirrors m_demo.m case 10: UTM projection of NE USA, GSHHS intermediate
coastline, fancy box, scale bar, animated ship track, north arrow.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
import py_m_map as mm


OUTPUT_DIR = Path(__file__).parent / 'outputs'


def test_example10():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 8), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.reset_state()
    mm.m_proj('utm', lon=[-72, -68], lat=[40, 44])

    mm.m_gshhs_i('line', color='k')
    mm.m_grid(box='fancy', tickdir='in', fontsize=6, xtick=1, ytick=1)
    mm.m_ruler([0.55, 0.90], 0.15, nbar=4, fontsize=7)

    # Ship track: 41 points along a great-circle arc
    lons = np.arange(-71, -66.9, 0.1)   # 41 points
    lats = 60 * np.cos(np.radians(lons + 115))
    navtimes = [datetime(1997, 10, 23, 15, i, 0) for i in range(1, 42)]

    mm.m_track(lons, lats, navtimes,
               ticks=0, times=4, dates=8,
               clip='off', color='r', orient='upright', fontsize=6)

    mm.m_northarrow(-68.5, 43.4, 0.4, type=2)

    out = OUTPUT_DIR / 'example10.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example10()
