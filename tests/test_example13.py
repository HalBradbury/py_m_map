"""
Test / reference output for Example 13 — Blue Ocean great-circle routes.
Mirrors m_demo.m case 13: Miller projection, green land patch, blue ocean
background, and three great-circle routes from Vancouver to Cairo, Washington,
and Buenos Aires.
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


def test_example13():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 5), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.reset_state()
    mm.m_proj('miller', lat=[-77, 77])

    mm.m_coast('patch', color=[0.7, 1.0, 0.7], edgecolor='none')
    mm.m_grid(box='fancy', linestyle='-', gridcolor='w', backcolor=[0.2, 0.65, 1.0])

    cities = ['Cairo', 'Washington', 'Buenos Aires']
    lons = [30 + 2/60, -77 - 2/60, -58 - 22/60]
    lats = [31 + 21/60, 38 + 53/60, -34 - 45/60]
    van_lon = -123 - 6/60
    van_lat =  49 + 13/60

    for k in range(3):
        dist, ln, lt = mm.m_lldist([van_lon, lons[k]], [van_lat, lats[k]], 40)
        mm.m_line(ln[0], lt[0], color='r', linewidth=2)
        mm.m_text(ln[0, -1], lt[0, -1],
                  f'{cities[k]} — {round(dist[0])} km',
                  fontsize=8, ha='left')

    out = OUTPUT_DIR / 'example13.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example13()
