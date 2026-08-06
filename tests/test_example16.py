"""
Test / reference output for Example 16 — NE Pacific bathymetry.

Lambert conformal conic projection of the NE Pacific Ocean with ETOPO1 filled
contours (blues colormap, ocean only, gamma-corrected for perceptual depth
emphasis), gray land fill via GSHHS intermediate coastlines, Line P
oceanographic station markers, Juan de Fuca Ridge hydrothermal vent markers,
a ruler-style fancy box, a horizontal depth colorbar, and a legend.

Reference image: m_map/doc/exbathym.png

Python equivalent of MATLAB website Example 16:
    m_proj('mercator','lon',[-155 -117],'lat',[33 62]);
    colormap(m_colmap('blues'));  caxis([-6000 0]);
    [CS,CH]=m_etopo2('contourf',[-6000:1000:0],'edgecolor','none');
    m_gshhs_f('patch',[.75 .75 .75]);
    m_line(linep_lon,linep_lat,'marker','o','color','r',...
           'linestyle','none','markersize',8,'markerfacecolor','none');
    m_line(vent_lon,vent_lat,'marker','s','color','g',...
           'linestyle','none','markersize',6,'markerfacecolor','none');
    m_grid('box','fancy','tickdir','out');
    ax=m_contfbar([.55 .97],.93,CS,CH,'axfrac',.04,'endpiece','no');
    title(ax,'meters');

Notes
-----
* Uses Lambert conformal conic (not Mercator) to match the reference image
  curved boundary.
* A gamma-corrected blues colormap (gamma=0.5) allocates more colour range to
  shallow depths, reproducing the reference image's visual emphasis on coastal
  bathymetry.
* The ruler-style fancy box ('boxstyle'='line') matches the reference border.
* Uses m_gshhs_i (intermediate) rather than m_gshhs_f (full) for this
  regional-scale map.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import py_m_map as mm

OUTPUT_DIR = Path(__file__).parent / 'outputs'

# Approximate Line P station positions (P26=Station Papa → P1 near-shore)
_LINEP_LON = [-145.0, -140.0, -137.0, -134.7, -132.5, -130.7,
              -129.6, -128.5, -127.5, -126.7, -125.5, -124.9]
_LINEP_LAT = [50.0, 49.5, 49.2, 49.0, 48.8, 48.7,
              48.6, 48.6, 48.6, 48.6, 48.6, 48.6]

# Approximate Juan de Fuca Ridge hydrothermal vent positions
_VENT_LON = [-130.3, -130.0, -129.8, -129.5, -129.1, -128.7, -128.4,
             -127.9, -127.5, -127.1, -126.7, -126.4, -126.0, -125.7, -125.4]
_VENT_LAT = [44.7, 45.0, 45.4, 45.9, 46.4, 46.8, 47.3,
             47.6, 47.9, 48.1, 48.3, 48.4, 48.5, 48.5, 48.6]


def test_example16():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    fig, ax = plt.subplots(figsize=(10, 9), facecolor='white')
    plt.sca(ax)

    mm.m_proj('lambert', lon=[-155, -117], lat=[33, 62])

    # Finer depth levels with extra resolution in shallow water.
    # The coarser 1000 m spacing covers the deep ocean; 500 m and 200 m
    # intervals capture the continental shelf and slope where colour
    # variation matters most visually.
    levels = np.array([-6000, -5000, -4000, -3000, -2000, -1000, -500, -200, 0],
                      dtype=float)

    # Gamma-corrected blues colormap — one colour per depth interval.
    # Gamma < 1 stretches the shallow end of the colour range so the
    # continental shelf and slope show more variation.
    gamma = 0.5
    n_intervals = len(levels) - 1
    t_linear = np.linspace(0.0, 1.0, n_intervals)
    t_gamma = t_linear ** gamma
    blues_raw = np.array(mm.m_colmap('blues', 256).colors)
    blues_sampled = np.array([blues_raw[int(round(v * 255))] for v in t_gamma])
    cmap = mcolors.ListedColormap(blues_sampled)

    # ETOPO1 filled contours (ocean only)
    mm.m_etopo2('contourf', levels, edgecolor='none', cmap=cmap, vmin=-6000, vmax=0)

    # GSHHS intermediate coastlines (gray land fill)
    mm.m_gshhs_i('patch', facecolor=[0.75, 0.75, 0.75], edgecolor='none')

    # Line P oceanographic stations (red open circles)
    mm.m_line(
        _LINEP_LON, _LINEP_LAT,
        marker='o', color='r', linestyle='none',
        markersize=8, fillstyle='none', markeredgewidth=1.5,
    )

    # Juan de Fuca Ridge hydrothermal vents (green open squares)
    mm.m_line(
        _VENT_LON, _VENT_LAT,
        marker='s', color='g', linestyle='none',
        markersize=6, fillstyle='none', markeredgewidth=1.2,
    )

    mm.m_grid(box='fancy', boxstyle='line', tickdir='out')

    # Horizontal colorbar: shorter and lower than the map edge so it sits
    # entirely within the map interior without crossing the frame boundary.
    cbar_ax, cb = mm.m_contfbar(
        [0.475, 0.725], 0.82,
        levels.reshape(-1, 1), levels,
        colormap=cmap, caxis=(-6000, 0),
        axfrac=0.04, endpiece=False,
    )
    cb.set_ticks(np.arange(-6000, 1, 2000))
    cbar_ax.set_title('meters', fontsize=8, fontweight='bold')

    # Legend positioned in the lower-left interior, high enough to clear
    # the curved conic corner masks.
    legend_elements = [
        Line2D([0], [0], marker='s', color='g', linestyle='none',
               markerfacecolor='none', markersize=6, markeredgewidth=1.2,
               label='Potential Cruise Stations'),
        Line2D([0], [0], marker='o', color='r', linestyle='none',
               markerfacecolor='none', markersize=8, markeredgewidth=1.5,
               label='Line-P Stations'),
    ]
    ax.legend(handles=legend_elements, loc='lower left',
              bbox_to_anchor=(0.05, 0.10),
              framealpha=1.0, edgecolor='k', fontsize=8)

    out = OUTPUT_DIR / 'example16.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_example16()
