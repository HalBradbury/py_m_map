"""
Example 20 — m_colmap colourmap gallery.

Three-column layout matching the m_map HTML example 20 gallery (exColmaps.png).
Panels are labelled a–t in the same column-major order as the MATLAB reference.

Special panels:
  q) Combined blues(64)+gland(128) — "Complex water+land example"
  t) odv(256) with cosine shading — "Isoluminant (with added shading)"

MATLAB equivalent:
    m_colmap demo
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

_NCOLS = 3

# ---------------------------------------------------------------------------
# Pre-compute the two special composite colormaps (q and t).
# ---------------------------------------------------------------------------
def _make_cmap_q():
    """[m_colmap('blues',64); m_colmap('gland',128)] — water + land composite."""
    blues = np.array(mm.m_colmap('blues', 64).colors)
    gland = np.array(mm.m_colmap('gland', 128).colors)
    from matplotlib.colors import ListedColormap
    return ListedColormap(np.vstack([blues, gland]).astype(np.float32))


def _make_cmap_t():
    """m_colmap('odv',256) .* (1 - 0.2*cos(i/64*2*pi)^4) — odv with shading."""
    odv = np.array(mm.m_colmap('odv', 256).colors)
    t = np.arange(256)
    shading = 1.0 - 0.2 * np.cos(t / 64.0 * 2.0 * np.pi) ** 4
    from matplotlib.colors import ListedColormap
    return ListedColormap(np.clip(odv * shading[:, None], 0.0, 1.0).astype(np.float32))


_CMAP_Q = _make_cmap_q()
_CMAP_T = _make_cmap_t()

# ---------------------------------------------------------------------------
# Gallery entries.
# Regular: (name, n, ncol, letter, description)
# Special: (title_str, None, None, letter, description, cmap_object)
# None     = blank cell.
# ---------------------------------------------------------------------------
_COLMAPS = [
    # Row 1
    ('jet',            256, 16, 'a', "Perceptually uniform jet replacement\nwith diverging luminance"),
    ('blues',          256, 16, 'g', "Good for bathymetry"),
    ('bland',          256, 16, 'n', "Land without green"),
    # Row 2
    ('mBOD',           256, 16, 'b', "Modified BOD with white removed\ncolorblind-friendly jet alternative"),
    ('water',          256, 16, 'h', "Another bathymetry map"),
    ('land',           256, 16, 'o', "Land from coastal wetlands to mountains"),
    # Row 3
    ('rBOD',           256, 16, 'c', "Reverse BOD\ncolorblind-friendly alternative"),
    ('green',          256, 16, 'i', "Chlorophyll? Land?"),
    ('gland',          256, 16, 'p', "Land with more green"),
    # Row 4
    ('diverging',      256, 16, 'd', "Currents, echo-sounder images\ndiverging luminance with a 'zero'"),
    ('chlorophyll',    256, 16, 'j', "Enhanced Chlorophyll\nemphasizing high values"),
    None,
    # Row 5
    ('BOD',            256, 16, 'e', "Blue-orange diverging"),
    ('CBchlorophyll',  256, 16, 'k', "Enhanced Chlorophyll\ncolorblind-friendly alternative"),
    ("[m_colmap('blues',64);m_colmap('gland',128)]", None, None, 'q',
     "Complex water + land example\nmust use 'caxis' to get coastline correct",
     _CMAP_Q),
    # Row 6
    ('odv',            256, 16, 'f', "Isoluminant"),
    ('2cyclic',        256, 16, 'l', "Cyclic, for angles with 2 dark regions"),
    None,
    # Row 7
    None,
    ('1cyclic',        256, 16, 'm', "Cyclic, for angles with 1 dark region"),
    None,
    # Row 8 — special banding / discrete / derived demos
    ('jet',           'step', 10, 'r', "Banded continuous map (256 colours)\nsort of like contouring"),
    ('jet',            10,   16, 's', "A few discrete steps (10 colours)"),
    ("m_colmap('odv',256).*(1-0.2*cos(i/64*2π)⁴)", None, None, 't',
     "Isoluminant (with added shading)",
     _CMAP_T),
]


def _call_str(name: str, n, ncol: int) -> str:
    if n is None:
        return name  # pre-formatted title string
    if isinstance(n, str):
        return f"m_colmap('{name}','{n}',{ncol})"
    if n == 256:
        return f"m_colmap('{name}',256)"
    return f"m_colmap('{name}',{n})"


def test_example20():
    OUTPUT_DIR.mkdir(exist_ok=True)

    n_cells = len(_COLMAPS)
    n_rows = (n_cells + _NCOLS - 1) // _NCOLS

    fig, axes = plt.subplots(n_rows, _NCOLS,
                             figsize=(13, n_rows * 1.9 + 0.4),
                             facecolor='white')
    axes = np.array(axes)

    fig.subplots_adjust(left=0.03, right=0.99, top=0.98, bottom=0.02,
                        hspace=1.2, wspace=0.22)

    gradient = np.linspace(0, 1, 256).reshape(1, -1)

    for idx, entry in enumerate(_COLMAPS):
        row, col = divmod(idx, _NCOLS)
        ax = axes[row, col]

        if entry is None:
            ax.set_visible(False)
            continue

        if len(entry) == 6:
            name, n, ncol, letter, description, cmap = entry
        else:
            name, n, ncol, letter, description = entry
            cmap = mm.m_colmap(name, n, ncol)

        ax.imshow(gradient, aspect='auto', cmap=cmap, extent=[0, 256, 0, 1])
        ax.set_yticks([])
        ax.set_xticks([])

        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

        title = f"{letter}) {_call_str(name, n, ncol)}"
        ax.set_title(title, fontsize=7.5, loc='left', pad=3,
                     fontfamily='monospace', color='#111111')

        ax.set_xlabel(description, fontsize=7.5, labelpad=4, loc='left')

    out = OUTPUT_DIR / 'example20.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example20()
