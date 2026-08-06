"""
Example 1 — M_Map Logo (orthographic globe view).

Run directly:

    python tests/test_example1.py

Output is saved to tests/outputs/example1.png.

Python equivalent of the MATLAB code (from map.html, Example 1):

    m_proj('ortho','lat',48,'long',-123);
    m_coast('patch','r');
    m_grid('linest','-','xticklabels',[],'yticklabels',[]);

Notes
-----
* ortho lat/lon are the globe centre, not an extent.
* Natural Earth 110m land polygons replace m_map's built-in coast database.
* Cartopy downloads Natural Earth data on first run (~1 MB, cached automatically).
"""
from __future__ import annotations
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from py_m_map import m_proj, m_grid, m_coast, m_text, reset_state


def run_example1(out_path: str = 'outputs/example1.png'):
    """Reproduce Example 1 and save to out_path."""
    reset_state()

    fig, ax = plt.subplots(1, 1, figsize=(6, 6))

    m_proj('ortho', lat=48, lon=-123)
    m_coast('patch', 'r')
    m_grid(linestyle='-', xticklabels=False, yticklabels=False)
    m_text(-123, 10, 'Py_M_Map',
           fontweight='bold',
           fontsize=30,
           ha='center', va='center',
           bbox=dict(boxstyle='square,pad=0.4',
                     facecolor='white', edgecolor='black', linewidth=1.5))

    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example1():
    out = os.path.join(_HERE, 'outputs', 'example1.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example1(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example1.png')
    run_example1(out)
