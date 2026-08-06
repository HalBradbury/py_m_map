"""
Test / reference output for Example 11 — Hammer projection with range rings.
Mirrors m_demo.m case 11: Hammer projection centred at 170°E, GSHHS coastline
patch, Bangkok marker, and 15 range rings at 1000 km intervals.
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


def test_example11():
    OUTPUT_DIR.mkdir(exist_ok=True)

    fig, ax = plt.subplots(figsize=(8, 5), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.reset_state()
    mm.m_proj('hammer', lon=170, lat=[-90, 90])

    mm.m_coast('patch', color=[0, 0.6, 0])
    mm.m_grid(grid='off')

    mm.m_line(100.5, 13.5, marker='s', color='r', linestyle='none', markersize=6)
    mm.m_range_ring(100.5, 13.5, np.arange(1000, 16000, 1000),
                    color='b', linewidth=2)

    ax.set_xlabel('1000 km range rings from Bangkok')

    out = OUTPUT_DIR / 'example11.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example11()
