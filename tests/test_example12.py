"""
Test / reference output for Example 12 — Lambert conic of BC coast.
Mirrors m_demo.m case 12: Lambert conic [-130 -121.5] × [47 51],
GSHHS intermediate coastline (line + speckle), hatched boundary polygon,
text annotation, and north arrow type 3.
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

BNDRY_LON = [-128.8, -128.8, -128.3, -128, -126.8, -126.6, -128.8]
BNDRY_LAT = [49, 50.33, 50.33, 50, 49.5, 49, 49]


def test_example12():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 6), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.reset_state()
    mm.m_proj('lambert', lon=[-130, -121.5], lat=[47, 51])

    # Coastline: lines then speckle texture on land
    mm.m_gshhs_i('line', color='k')
    mm.m_gshhs_i('speckle', color='k')

    # Boundary polygon with hatch fill
    mm.m_line(BNDRY_LON, BNDRY_LAT, linewidth=2, color='k')
    mm.m_hatch(BNDRY_LON, BNDRY_LAT, 'single', 30, 5, color='k')

    mm.m_grid(linewidth=2, linestyle='none')

    mm.m_text(-128, 48, ['Pacific', 'Ocean'], fontsize=18)
    mm.m_northarrow(-122.5, 50.2, 0.8, type=3, linewi=2)

    out = OUTPUT_DIR / 'example12.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example12()
