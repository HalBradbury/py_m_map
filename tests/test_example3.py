"""
Example 3 — Polar Stereographic projection of the North Polar region.

Run directly:

    python tests/test_example3.py

Output saved to tests/outputs/example3.png.

Python equivalent of the MATLAB code (from map.html, Example 3):

    m_proj('stereographic','lat',90,'long',30,'radius',25);
    m_elev('contour',[-3500:1000:-500],'edgecolor','b');
    m_grid('xtick',12,'tickdir','out','ytick',[70 80],'linest','-');
    m_coast('patch',[.7 .7 .7],'edgecolor','r');

Notes
-----
* The coastline is drawn after the grid so it appears on top — as noted in the
  original m_map documentation ("Note that coastline is drawn OVER the grid
  because of the order in which the two routines are called").
* m_elev loads m_topo.mat from the companion m_map/private/ directory.
* xtick=12 generates meridians every 12° (30 meridians total).
* ytick=[70, 80] draws parallels at 70°N and 80°N only.
* 'edgecolor' is the MATLAB m_contour kwarg for line colour; py_m_map maps it
  to matplotlib's 'colors'.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from py_m_map import m_proj, m_grid, m_coast, m_elev, reset_state


def run_example3(out_path: str = 'outputs/example3.png'):
    """Reproduce Example 3 and save to out_path."""
    reset_state()

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    m_proj('stereographic', lat=90, lon=30, radius=25)

    # Blue bathymetric contours (ocean floor depths)
    m_elev('contour', np.arange(-3500, -499, 1000), edgecolor='b')

    # Grid: meridians every 30°, parallels at 70°N and 80°N, ticks outward
    # Latitude labels placed along the 170°W meridian (open ocean, unobstructed)
    m_grid(xtick=30, tickdir='out', ytick=[70, 80], linest='-', lat_label_lon=-170)

    # Land as grey patch with red outline — drawn last so it sits on top of grid
    m_coast('patch', [0.7, 0.7, 0.7], edgecolor='r')

    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example3():
    out = os.path.join(_HERE, 'outputs', 'example3.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example3(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example3.png')
    run_example3(out)
