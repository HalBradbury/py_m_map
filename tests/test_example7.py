"""
Example 7 — Lambert Conformal Conic — Europe/Mediterranean topography + colourbar.

Run directly:

    python tests/test_example7.py

Output saved to tests/outputs/example7.png.

Python equivalent of MATLAB Example 7 (from m_demo.m, case 7):

    m_proj('lambert','lon',[-10 20],'lat',[33 48]);
    [CS,CH]=m_etopo2('contourf',[-5000:500:0 250:250:3000],'edgecolor','none');
    m_grid('linestyle','none','tickdir','out','linewidth',3);
    colormap([ m_colmap('blues',80); m_colmap('gland',48)]);
    brighten(.5);
    ax=m_contfbar(1,[.5 .8],CS,CH);
    title(ax,{'Level/m',''});

Notes
-----
* m_etopo2 is not implemented; m_elev (1° ETOPO-derived database) is used instead,
  exactly as MATLAB does when the ETOPO2 binary is not present.
* brighten(0.5) raises each RGB value to the power (1 - 0.5) = 0.5 (sqrt).
* The combined colormap (80 blues + 48 gland = 128 colours) maps linearly from
  -5000 m to 3000 m, so blues cover exactly the ocean range and gland the land range.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from py_m_map import m_proj, m_grid, m_etopo2, m_colmap, m_contfbar, reset_state


def _brighten(rgb: np.ndarray, f: float) -> np.ndarray:
    """MATLAB brighten(f) for 0 < f < 1: raises RGB to power (1 - f)."""
    return np.clip(np.asarray(rgb, dtype=float) ** (1.0 - f), 0.0, 1.0)


def run_example7(out_path: str = 'outputs/example7.png'):
    """Reproduce Example 7 and save to out_path."""
    reset_state()

    # Combined colormap: 80 blues (ocean) + 48 gland (land), then brighten(0.5).
    # Linear norm from -5000 to 3000 means blues cover exactly ocean, gland = land.
    blues = m_colmap('blues', 80)
    gland = m_colmap('gland', 48)
    cmap_rgb = _brighten(np.vstack([blues.colors, gland.colors]), 0.5)
    cmap = ListedColormap(cmap_rgb)
    norm = Normalize(vmin=-5000, vmax=3000)

    # Contour levels: 500 m intervals for ocean, 250 m for land
    levels = np.concatenate([np.arange(-5000, 1, 500),
                             np.arange(250, 3001, 250)])

    fig, ax = plt.subplots(figsize=(9, 7))

    m_proj('lambert', lon=[-10, 20], lat=[33, 48])
    m_etopo2('contourf', levels, edgecolor='none', cmap=cmap, norm=norm)
    m_grid(linestyle='none', tickdir='out', linewidth=3)

    cbar_ax, cb = m_contfbar(
        1.12, [.5, .8], levels, levels,
        colormap=cmap, caxis=(-5000, 3000),
        endpiece=False,
    )
    cbar_ax.set_title('Level/m', fontsize=8)

    plt.tight_layout()
    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example7():
    out = os.path.join(_HERE, 'outputs', 'example7.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example7(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example7.png')
    run_example7(out)
