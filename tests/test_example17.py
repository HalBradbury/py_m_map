"""
Test / reference output for Example 17 — South China Sea shaded relief.

Mercator projection of the South China Sea with ETOPO1 shaded relief
rendered using a white-to-blue colormap (white = shallow, dark blue = deep),
GSHHS high-resolution coastlines, a fancy grid box, and a vertical depth
colorbar on the right.

Reference image: m_map/doc/SouthChinaSea.png

Python equivalent of MATLAB website Example 17:
    m_proj('mercator','lon',[105 124],'lat',[5 24]);
    colormap(jet); caxis([-6000 0]);
    m_etopo2('shadedrelief');
    m_gshhs_i('patch',[.7 .7 .7]);
    m_grid('linestyle','-','tickdir','out');
    ax=m_contfbar(1,[.15 .90],z_rng,z_rng,'axfrac',.04,'endpiece','no');
    title(ax,'meters');

Notes
-----
* Uses GSHHS high-resolution coastlines (m_gshhs_h) for better coastal detail.
* Blues_r colormap: vmin=-6000 maps to dark blue, vmax=0 maps to white,
  giving white shallow water and dark blue deep ocean.
* Fancy grid box matches the reference border style.
* Vertical colorbar is positioned to the right of the axes.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import py_m_map as mm

OUTPUT_DIR = Path(__file__).parent / 'outputs'


def test_example17():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    fig, ax = plt.subplots(figsize=(8, 8), facecolor='white')
    plt.sca(ax)

    mm.m_proj('mercator', lon=[105, 124], lat=[5, 24])

    # Depth colormap: white (0 m, shallow) → blue → green → yellow → red (-6000 m, deep).
    # mm.m_colmap('depth') index 0=red (deep), index 255=white (shallow),
    # matching caxis=(-6000, 0): vmin=-6000→red, vmax=0→white.
    depth_levels = np.arange(-6000, 1, 1000)
    depth_cmap = mm.m_colmap('depth', 256)

    # ETOPO1 shaded relief with white-to-blue colormap
    mm.m_etopo2('shadedrelief', colormap=depth_cmap, caxis=(-6000, 0))

    # GSHHS high-resolution coastlines drawn on top to mask land
    mm.m_gshhs_h('patch', facecolor=[0.70, 0.70, 0.70], edgecolor='none')

    mm.m_grid(linestyle='-', tickdir='out', box='fancy')

    # Vertical depth colorbar to the right of the map
    cbar_ax, cb = mm.m_contfbar(
        1.08, [0.15, 0.90],
        depth_levels.reshape(-1, 1), depth_levels,
        colormap=depth_cmap, caxis=(-6000, 0),
        axfrac=0.04, endpiece=False,
    )
    cbar_ax.set_title('meters', fontsize=8, fontweight='bold')

    out = OUTPUT_DIR / 'example17.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example17()
