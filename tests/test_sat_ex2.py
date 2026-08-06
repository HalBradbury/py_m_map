"""
Satellite Example 2 — Arctic sea-ice concentration, azimuthal equal-area.

Follows map.html satellite example 2 (Pawlowicz), which mapped an SSM/I EASE-Grid
sea-ice product:

    m_proj('azimuthal equal-area','latitude',90,'radius',47,'rectbox','on');
    offs=9036842.762500/6371228;
    image([-offs offs],[offs -offs],P); set(gca,'ydir','normal');
    colormap([.2 .5 .2; jet(100); 1 1 1; 0 0 0; .9 .9 .9; .8 .8 .8; 0 0 .5]);
    caxis([0 105]);
    m_coast('color','k');
    m_grid('linewi',2,'tickdir','out');

Data
----
NOAA OI SST V2 monthly sea-ice concentration (Reynolds et al., 2002), 1° global
grid, downloaded from NOAA PSL on first run and cached in ~/.py_m_map/ — see
tests/example_data.py.

September 2012 is used: the record Arctic sea-ice minimum, which makes the ice
edge and the marginal ice zone unusually clear.  Compare with March for the
seasonal maximum by changing TARGET_MONTH.

Unlike the MATLAB original this maps a geographic lon/lat field with m_pcolor
rather than pushing raw EASE-Grid projection coordinates through image(), so no
hard-coded grid offset is needed.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import xarray as xr
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import py_m_map as mm
import example_data

OUTPUT_DIR = Path(__file__).parent / 'outputs'

TARGET_MONTH = '2012-09'
CAP_RADIUS = 47.0            # degrees of arc from the pole, as in the original
MIN_LAT = 90.0 - CAP_RADIUS - 2.0


def _load_ice():
    """
    Monthly sea-ice concentration over the Arctic cap.

    Returns
    -------
    lon, lat : 1-D arrays, ascending
    conc : 2-D (n_lat, n_lon), per cent; NaN where there is no ocean
    """
    (path,) = example_data.require('icec.mnmean.nc')
    cftime = xr.coders.CFDatetimeCoder(use_cftime=True)
    with xr.open_dataset(path, decode_times=cftime) as ds:
        field = (ds['icec']
                 .sel(time=TARGET_MONTH)
                 .squeeze()
                 .sortby('lat')
                 .sel(lat=slice(MIN_LAT, 90.0)))
        lat = field.lat.values.astype(float)
        lon = field.lon.values.astype(float)
        conc = field.values.astype(float)

    # 0.5…359.5 east -> -180…180, re-sorted so the grid stays monotonic.
    lon = ((lon + 180.0) % 360.0) - 180.0
    order = np.argsort(lon)
    return lon[order], lat, conc[:, order]


def test_sat_ex2():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    lon, lat, conc = _load_ice()
    lon_g, lat_g = np.meshgrid(lon, lat)

    # Open water (0 %) is kept rather than masked: with the ramp running blue to
    # white it renders as ocean, which is both the conventional way to show sea
    # ice and what distinguishes ice-free water from 100 % cover.  The NaNs that
    # remain are land, and the coastline patch covers those.

    fig, ax = plt.subplots(figsize=(8, 8), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('azimuthal equal-area', lat=90, lon=0, radius=CAP_RADIUS)

    # Reversed Blues: 0 % ice is deep blue (open ocean), 100 % is white (solid
    # pack).  Truncated at the dark end only, so the deepest ocean blue stays
    # distinguishable from the land colour.
    ice_cmap = mcolors.ListedColormap(
        plt.cm.Blues(np.linspace(0.85, 0.0, 100))[:, :3]
    )

    mm.m_pcolor(lon_g, lat_g, conc, cmap=ice_cmap, vmin=0.0, vmax=100.0)

    mm.m_coast('patch', color=[0.2, 0.5, 0.2], edgecolor='k', linewidth=0.4)
    # lat_label_lon: by default latitude labels go at each parallel's left-most
    # point, which on a polar map is the 90 W meridian — right on top of that
    # meridian's own label.  75 W sits between two longitude ticks and is clear.
    mm.m_grid(tickdir='out', linewidth=1.0, lat_label_lon=-75.0)

    sm = plt.cm.ScalarMappable(cmap=ice_cmap,
                               norm=plt.Normalize(vmin=0, vmax=100))
    sm.set_array([])
    bar = fig.colorbar(sm, ax=ax, orientation='horizontal',
                       fraction=0.04, pad=0.04)
    bar.set_label(f'Sea-ice concentration, {TARGET_MONTH} (%)')

    out = OUTPUT_DIR / 'sat_ex2.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_sat_ex2()
