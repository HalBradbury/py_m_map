"""
Example 5 — Oblique Mercator Projection with quiver and contour data.

Run directly:

    python tests/test_example5.py

Output saved to tests/outputs/example5.png.

Python equivalent of MATLAB Example 5 (from map.html):

    [lon,lat]=meshgrid([-136:2:-114],[36:2:54]);
    u=sin(lat/6);v=sin(lon/6);

    m_proj('oblique','lat',[56 30],'lon',[-132 -120],'aspect',.8);
    subplot(121);
    m_coast('patch',[.9 .9 .9],'edgecolor','none');
    m_grid('tickdir','out','yaxislocation','right',...
                'xaxislocation','top','xlabeldir','end','ticklen',.02);
    hold on;
    m_quiver(lon,lat,u,v);
    xlabel('Simulated surface winds');
    subplot(122);
    m_coast('patch',[.9 .9 .9],'edgecolor','none');
    m_grid('tickdir','out','yticklabels',[],...
                  'xticklabels',[],'linestyle','none','ticklen',.02);
    hold on;
    [cs,h]=m_contour(lon,lat,sqrt(u.*u+v.*v));
    clabel(cs,h,'fontsize',8);
    xlabel('Simulated something else');
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

from py_m_map import m_proj, m_grid, m_coast, m_contour, m_quiver, reset_state


def run_example5(out_path: str = 'outputs/example5.png'):
    """Reproduce Example 5 and save to out_path."""
    reset_state()

    # Simulated data on a regular lon/lat grid
    lon_arr = np.arange(-136, -114 + 1, 2, dtype=float)
    lat_arr = np.arange(36, 54 + 1, 2, dtype=float)
    lon, lat = np.meshgrid(lon_arr, lat_arr)
    u = np.sin(lat / 6.0)
    v = np.sin(lon / 6.0)
    speed = np.sqrt(u**2 + v**2)

    # Map aspect is 0.8 (portrait). Two side-by-side → figure aspect = 2*0.8 = 1.6.
    # Extra height for labels → figsize=(12, 8).
    fig, axes = plt.subplots(1, 2, figsize=(12, 8))

    # One shared projection — both subplots use the same oblique setup.
    # m_proj is called once; state persists for both panels.
    m_proj('oblique', lat=[56, 30], lon=[-132, -120], aspect=0.8)

    # -----------------------------------------------------------------------
    # Left subplot: coastline + quiver
    # -----------------------------------------------------------------------
    plt.sca(axes[0])
    m_coast('patch', [0.9, 0.9, 0.9], edgecolor='none')
    m_grid(
        tickdir='out',
        yaxislocation='right',
        xaxislocation='top',
        ticklen=0.02,
    )
    m_quiver(lon, lat, u, v)
    axes[0].set_xlabel('Simulated surface winds', labelpad=12)

    # -----------------------------------------------------------------------
    # Right subplot: coastline + contour + clabel
    # -----------------------------------------------------------------------
    plt.sca(axes[1])
    m_coast('patch', [0.9, 0.9, 0.9], edgecolor='none')
    m_grid(
        tickdir='out',
        yticklabels=[],
        xticklabels=[],
        linestyle='none',
        ticklen=0.02,
    )
    cs = m_contour(lon, lat, speed)
    plt.clabel(cs, fontsize=8)
    axes[1].set_xlabel('Simulated something else', labelpad=12)

    plt.tight_layout()
    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example5():
    out = os.path.join(_HERE, 'outputs', 'example5.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example5(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example5.png')
    run_example5(out)
