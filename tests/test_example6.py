"""
Example 6 — Miller Cylindrical Projection with a circular orbit track.

Run directly:

    python tests/test_example6.py

Output saved to tests/outputs/example6.png.

Python equivalent of MATLAB Example 6 (from m_demo.m, case 6):

    lon=[-180:180];
    lat=atan(tan(60*pi/180)*cos((lon-30)*pi/180))*180/pi;

    m_proj('miller','lat',82);
    m_coast('color',[0 .6 0]);
    m_line(lon,lat,'linewidth',3,'color','r');
    m_grid('linestyle','none','box','fancy','boxstyle','line','tickdir','out');

    m_northarrow(-150,0,40,'type',4,'linewi',.5);

Notes
-----
* m_coast('color', ...) maps to m_coast('line', color=...) in py_m_map.
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

from py_m_map import m_proj, m_grid, m_coast, m_line, m_northarrow, reset_state


def run_example6(out_path: str = 'outputs/example6.png'):
    """Reproduce Example 6 and save to out_path."""
    reset_state()

    # Circular satellite orbit track
    lon = np.arange(-180, 181, dtype=float)
    lat = np.degrees(np.arctan(np.tan(np.radians(60.0)) * np.cos(np.radians(lon - 30.0))))

    fig, ax = plt.subplots(figsize=(10, 6))

    m_proj('miller', lat=82)
    m_coast('line', color=[0, 0.6, 0])
    m_line(lon, lat, linewidth=3, color='r')
    m_grid(linestyle='none', box='fancy', boxstyle='line', tickdir='out')
    m_northarrow(-150, 0, 40, type=4, linewi=0.5)

    plt.tight_layout()
    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example6():
    out = os.path.join(_HERE, 'outputs', 'example6.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example6(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example6.png')
    run_example6(out)
