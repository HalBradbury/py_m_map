"""
Example 2 — Lambert Conformal Conic projection of North American Topography.

Run directly:

    python tests/test_example2.py

Output saved to tests/outputs/example2.png.

Python equivalent of the MATLAB code (from map.html, Example 2):

    m_proj('lambert','long',[-160 -40],'lat',[30 80]);
    m_coast('patch',[1 .85 .7]);
    m_elev('contourf',[500:500:6000]);
    m_grid('box','fancy','tickdir','in');
    colormap(flipud(copper));

Notes
-----
* Standard parallels default to mean(lat) ± diff(lat)/6 (MATLAB mp_conic.m rule).
* m_elev loads m_topo.mat from the companion m_map/private/ directory.
* flipud(copper) → matplotlib 'copper_r' colormap.
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


def run_example2(out_path: str = 'outputs/example2.png'):
    """Reproduce Example 2 and save to out_path."""
    reset_state()

    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    m_proj('lambert', lon=[-160, -40], lat=[30, 80])

    # Sandy-coloured land underneath — drawn first so elevation contours overlay
    m_coast('patch', [1, 0.85, 0.7])

    # Filled topography contours (land only; ocean stays uncoloured)
    m_elev('contourf', np.arange(500, 6001, 500), cmap='copper_r')

    m_grid(box='fancy', tickdir='in')

    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example2():
    out = os.path.join(_HERE, 'outputs', 'example2.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example2(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example2.png')
    run_example2(out)
