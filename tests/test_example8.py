"""
Example 8 — Demonstration of fancy vectors (m_vec).

Run directly:

    python tests/test_example8.py

Output saved to tests/outputs/example8.png.

Python equivalent of MATLAB Example 8 (from map.html#examples and m_demo.m case 8):

    m_proj('ortho','lat',48,'long',-123,'rad',10,'rec','off');
    m_coast('patch',[0.9 0.95 0.9],'edgecolor','none');
    m_grid('linestyle',':','xtick',[-135:5:-110],'linewi',2,...
           'color',[.5 .5 .5],'fontsize',6);
    title('Demonstration of m_vec')

    m_vec(100, [-133 -133], [49 49], [0 50], [100 0.0], [0.7 0.8 0.9], ...
          'centered','yes', 'shaftwidth',5, 'headlength',0, 'EdgeColor','k');

    m_vec(100, [-119 -119 -119], [53 53 53], ...
          [0 25*sqrt(2) 50], [50 25*sqrt(2) 0]);

    incs = (1:20)/20;
    vlat = 42 + incs*3;  vlon = -127 - incs*2;
    uu = 50*sin(incs*2*pi);  vv = 50*cos(incs*2*pi);

    m_vec(100, vlon+12, vlat+2, uu, vv, 'm', ...
          'shaftwidth',0.2, 'headlength',2.5, 'curvature',30);

    m_vec(100, vlon-4, vlat, uu, vv, sst);
    ha2 = colorbar('southoutside');
    set(get(ha2,'xlabel'),'string','SST');

    m_vec(100, vlon+4, vlat-5, uu, vv, sst, 'edgeclip','on');
    m_vec(100, -115, 38, 50, 0, 'b', 'key', '50 cm s^{-1}');
    m_vec(100, -124, 53, 30, -40, 'r', 'curvature', 30);

    colormap(m_colmap('jet'));
"""
from __future__ import annotations
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from py_m_map import (m_proj, m_grid, m_coast, m_colmap, m_vec, reset_state)


def run_example8(out_path: str = 'outputs/example8.png'):
    reset_state()

    incs = np.arange(1, 21) / 20.0
    vlat = 42.0 + incs * 3.0
    vlon = -127.0 - incs * 2.0
    uu = 50.0 * np.sin(incs * 2 * np.pi)
    vv = 50.0 * np.cos(incs * 2 * np.pi)
    sst = 12.0 - incs * 4.0   # fake SST for colour-mapped vectors

    fig, ax = plt.subplots(figsize=(8, 7))

    m_proj('orthographic', lon=-123, lat=48, radius=10)
    m_coast('patch', facecolor=[0.9, 0.95, 0.9], edgecolor='none')
    m_grid(linestyle=':', xtick=np.arange(-135, -109, 5),
           linewidth=2, color=[0.5, 0.5, 0.5], fontsize=6)
    ax.set_title('Demonstration of m_vec', fontsize=10)

    # --- Two light-blue "variance ellipse" bars, centred, no head ---
    m_vec(100, [-133, -133], [49, 49],
          [0, 50], [100, 0],
          [0.7, 0.8, 0.9],
          centered='yes', shaftwidth=5, headlength=0, edgecolor='k')

    # --- Three black arrows showing 0°, 45°, 90° directions ---
    sq2 = 25.0 * np.sqrt(2)
    m_vec(100, [-119, -119, -119], [53, 53, 53],
          [0, sq2, 50], [50, sq2, 0])

    # --- Magenta cruise-track arrows with curvature ---
    m_vec(100, vlon + 12, vlat + 2, uu, vv, 'm',
          shaftwidth=0.2, headlength=2.5, curvature=30)

    # --- SST colour-mapped vectors (uses current colormap) ---
    jet_cmap = m_colmap('jet', 256)
    sst_norm = Normalize(vmin=sst.min(), vmax=sst.max())

    # Draw as individual patches coloured by SST
    for i in range(len(vlon)):
        c = jet_cmap(sst_norm(sst[i]))
        m_vec(100, [vlon[i] - 4], [vlat[i]], [uu[i]], [vv[i]], list(c[:3]))

    # Colorbar for SST below the axes
    sm = ScalarMappable(cmap=jet_cmap, norm=sst_norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation='horizontal', fraction=0.04,
                        pad=0.04, shrink=0.5)
    cbar.set_label('SST')

    # --- SST vectors with edge clipping ---
    for i in range(len(vlon)):
        c = jet_cmap(sst_norm(sst[i]))
        m_vec(100, [vlon[i] + 4], [vlat[i] - 5], [uu[i]], [vv[i]], list(c[:3]),
              edgeclip=True)

    # --- Key (legend) arrow ---
    m_vec(100, [-115], [38], [50], [0], 'b', key='50 cm s$^{-1}$')

    # --- Red curved arrow ---
    m_vec(100, [-124], [53], [30], [-40], 'r', curvature=30)

    plt.tight_layout()
    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example8():
    out = os.path.join(_HERE, 'outputs', 'example8.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example8(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example8.png')
    run_example8(out)
