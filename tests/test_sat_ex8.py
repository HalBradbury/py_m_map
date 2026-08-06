"""
Satellite Example 8 — Shaded Relief from a high-resolution topography (netCDF format).

From the "Examples of satellite data manipulation" section of map.html (example 8).
Run directly:

    python tests/test_sat_ex8.py

Output is saved to tests/outputs/sat_ex8.png for visual comparison with
the MATLAB reference image in ../m_map/map.html#satellite_examples.

Python equivalent of the MATLAB code (from map.html, satellite example 8):

    clat = [48+46/60  49+5/60];
    clon = [-125-15/60  -124-55/60];
    fname = 'barkley_sound_1_navd88_2016.nc';

    lat  = ncread(fname,'lat');
    lon  = ncread(fname,'lon');
    ilat = lat>=clat(1) & lat<=clat(2);
    ilon = lon>=clon(1) & lon<=clon(2);
    Z    = ncread(fname,'Band1', [find(ilon,1) find(ilat,1)], [sum(ilon) sum(ilat)], [1 1]);

    m_proj('equidistant','lon',clon,'lat',clat);

    subplot(1,2,2);
    caxis([-300 1210]);
    colormap([m_colmap('blues',32); m_colmap('gland',128)]);
    m_shadedrelief(lon(ilon),lat(ilat),Z');
    m_grid('box','fancy','grid','none','fontsize',14);
    m_contfbar([.3 .7],.98,Z',[-300:1210],'axfrac',.02,'endpiece','no',
               'levels','match','edgecolor','none');

    subplot(1,2,1);
    m_contourf(lon(ilon),lat(ilat),Z',[-300:25:-25 2 50:50:200 300:100:1200 1210]);
    caxis([-300 1210]);
    colormap([m_colmap('blues',32); m_colmap('gland',128)]);
    m_grid('box','fancy','tickdir','out','grid','none','fontsize',14);
    m_contfbar([.3 .7],.98,Z',[-300:25:-25 2 50:50:200 300:100:1200 1210],
               'axfrac',.02,'endpiece','no','levels','match');

Notes on Python vs MATLAB differences
--------------------------------------
* In MATLAB, ncread returns Band1 as (lon × lat), requiring Z' (transpose).
  In Python, xarray returns Band1 as (lat × lon) — no transpose needed.
* m_proj is called once; both subplots share the same projection state.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, Normalize

# Allow running from the tests/ directory or from the package root
_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from py_m_map import (
    m_proj, m_grid, m_colmap,
    m_shadedrelief, m_contourf, m_contour, m_contfbar,
    reset_state,
)

#: High-resolution Barkley Sound bathymetry.  Unlike the other example datasets
#: this one is not fetched: it is a large regional DEM with no stable open URL, so
#: it has to be supplied locally.  Searched beside the package root first (the
#: original layout), then on the shared data path used by everything else.
_DATAFILE_NAME = 'barkley_sound_1_navd88_2016.nc'

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from py_m_map._data import ENV_VAR, USER_DATA_DIR, resolve_data_file  # noqa: E402

def _datafile():
    """Local path to the bathymetry, or None if it is not installed."""
    legacy = os.path.join(_PKG_ROOT, '..', _DATAFILE_NAME)
    if os.path.isfile(legacy):
        return legacy
    found = resolve_data_file(_DATAFILE_NAME)
    return str(found) if found is not None else None


def run_sat_ex8(out_path: str = 'outputs/sat_ex8.png'):
    """Reproduce Example 8 and save to out_path."""
    import xarray as xr

    # ------------------------------------------------------------------ #
    # Data
    # ------------------------------------------------------------------ #
    clat = [48 + 46 / 60,  49 + 5 / 60]
    clon = [-125 - 15 / 60, -124 - 55 / 60]

    # The domain is only 20' of longitude wide and each subplot gets half the
    # figure, so the automatic degree-minute labels collide at fontsize 14.
    # Ten-minute longitude / five-minute latitude ticks leave them legible.
    xticks = np.arange(-125 - 10 / 60, -124.91, 10 / 60)
    yticks = np.arange(48 + 50 / 60, 49 + 0.01 / 60, 5 / 60)

    datafile = _datafile()
    if datafile is None:
        raise FileNotFoundError(
            f'{_DATAFILE_NAME} not found. This example needs a local copy of the '
            f'Barkley Sound DEM; place it in {USER_DATA_DIR}/ or set {ENV_VAR} to '
            f'the directory holding it.'
        )
    ds = xr.open_dataset(datafile)
    lat = ds['lat'].values   # shape (1476,)
    lon = ds['lon'].values   # shape (2448,)

    ilat = (lat >= clat[0]) & (lat <= clat[1])
    ilon = (lon >= clon[0]) & (lon <= clon[1])

    # xarray Band1 is already (lat, lon) — no transpose needed
    Z = ds['Band1'].values[np.ix_(ilat, ilon)].astype(float)

    # ------------------------------------------------------------------ #
    # Shared map setup
    # ------------------------------------------------------------------ #
    reset_state()
    m_proj('equidistant', lon=clon, lat=clat)

    cmap_arr = np.vstack([m_colmap('blues', 32).colors, m_colmap('gland', 128).colors])
    listed_cmap = ListedColormap(cmap_arr)
    norm = Normalize(vmin=-300, vmax=1210)

    # Contour levels matching the MATLAB example:
    #   [-300:25:-25  2  50:50:200  300:100:1200  1210]
    levels_contour = np.concatenate([
        np.arange(-300, -24, 25),   # -300, -275, ..., -25
        [2],
        np.arange(50, 201, 50),     # 50, 100, 150, 200
        np.arange(300, 1201, 100),  # 300, 400, ..., 1200
        [1210],
    ])

    # ------------------------------------------------------------------ #
    # Figure
    # ------------------------------------------------------------------ #
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    # Leave room to the right of each subplot for the vertical colourbar
    plt.subplots_adjust(right=0.87, wspace=0.35)

    # ------------------------------------------------------------------ #
    # Right subplot — shaded relief
    # ------------------------------------------------------------------ #
    plt.sca(ax2)
    m_shadedrelief(
        lon[ilon], lat[ilat], Z,
        colormap=cmap_arr,
        caxis=(-300, 1210),
    )
    m_grid(box='fancy', grid='none', fontsize=14,
           xtick=xticks, ytick=yticks)
    # xpos > 1.0 places the bar to the right of the axes; ypos=[y0,y1] → vertical
    m_contfbar(
        1.05, [0.0, 1.0], Z, np.arange(-300, 1211),
        colormap=listed_cmap, caxis=(-300, 1210),
        axfrac=0.06, endpiece=False, levels_mode='match', edgecolor='none',
    )

    # ------------------------------------------------------------------ #
    # Left subplot — filled contours + black contour lines on top
    # ------------------------------------------------------------------ #
    plt.sca(ax1)
    m_contourf(
        lon[ilon], lat[ilat], Z,
        levels_contour,
        cmap=listed_cmap, norm=norm,
    )
    # Black contour lines on top (standard MATLAB contourf appearance)
    m_contour(
        lon[ilon], lat[ilat], Z,
        levels_contour,
        colors='k', linewidths=0.4,
    )
    m_grid(box='fancy', tickdir='out', grid='none', fontsize=14,
           xtick=xticks, ytick=yticks)
    m_contfbar(
        1.05, [0.0, 1.0], Z, levels_contour,
        colormap=listed_cmap, caxis=(-300, 1210),
        axfrac=0.06, endpiece=False, levels_mode='match',
    )

    # ------------------------------------------------------------------ #
    # Save
    # ------------------------------------------------------------------ #
    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else '.', exist_ok=True)
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_sat_ex8():
    if _datafile() is None:
        import pytest
        pytest.skip(
            f'{_DATAFILE_NAME} is not installed. It is a large regional DEM with '
            f'no stable open URL, so unlike the other example datasets it cannot '
            f'be fetched — place it in {USER_DATA_DIR}/ or set {ENV_VAR}.'
        )
    out = os.path.join(_HERE, 'outputs', 'sat_ex8.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_sat_ex8(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'sat_ex8.png')
    run_sat_ex8(out)
