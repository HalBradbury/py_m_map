"""
Satellite Example 1 — Global SST on a Hammer-Aitoff projection.

Follows map.html satellite example 1 (Pawlowicz), which mapped the NOAA/NASA
Pathfinder AVHRR SST product for November 1999:

    [P,map]=imread('../m_mapWK/199911h54ma-gdm.hdf');
    P=0.15*double(P)-3;
    Plat=90-.25-[0:359]*.5; Plon=-180+.25+[0:719]*.5;
    [Plg,Plt]=meshgrid(Plon-0.25,Plat+0.25);
    m_proj('hammer-aitoff','clongitude',-150);
    m_pcolor(Plg,Plt,P);   shading flat;  colormap(map);
    hold on;
    m_pcolor(Plg-360,Plt,P); shading flat; colormap(map);
    m_coast('patch',[.6 1 .6]);
    m_grid('xaxis','middle');
    h=colorbar('h');
    set(get(h,'xlabel'),'string','AVHRR SST Nov 1999');

Data
----
NOAA OI SST V2 monthly means (Reynolds et al., 2002), 1° global grid, downloaded
from NOAA PSL on first run and cached in ~/.py_m_map/ — see tests/example_data.py.
The same month as the original example is used, so this is the real field the
MATLAB version illustrated, at 1° rather than 0.5° resolution.

The MATLAB version draws the field twice, at lon and lon-360, to fill the half of
the map left empty when a Hammer-Aitoff centred on 150°W straddles the data's wrap
point.  That is not needed here: py_m_map reports lon_limits of (-180, 180) for
this projection and a single call recentred onto -180…180 covers the whole map, so
the second call would be pure redundancy.

It would no longer be harmful, though.  It used to be: m_pcolor sent off-map cells
through the colormap's "bad" colour, so a fully out-of-range copy painted the whole
figure whenever that colour was opaque — which is how this example first came out
blank.  Off-map cells are now drawn transparent instead (REVIEW.md M9).
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))
import py_m_map as mm
import example_data

OUTPUT_DIR = Path(__file__).parent / 'outputs'

TARGET_MONTH = '1999-11'
CLON = -150.0
SST_RANGE = (-2.0, 30.0)


def _load_sst():
    """
    November 1999 monthly-mean SST on a −180…180 longitude grid.

    Returns
    -------
    lon, lat : 1-D arrays, ascending
    sst : 2-D (n_lat, n_lon), degrees Celsius, NaN over land
    """
    (path,) = example_data.require('sst.mnmean.nc')
    cftime = xr.coders.CFDatetimeCoder(use_cftime=True)
    with xr.open_dataset(path, decode_times=cftime) as ds:
        field = ds['sst'].sel(time=TARGET_MONTH).squeeze()
        lat = field.lat.values.astype(float)
        lon = field.lon.values.astype(float)
        sst = field.values.astype(float)

    # OISST runs 0.5…359.5 east; the projection is centred at 150 W, so recentre
    # onto -180…180 and re-sort rather than relying on wrap-around behaviour.
    lon = ((lon + 180.0) % 360.0) - 180.0
    order = np.argsort(lon)
    lon = lon[order]
    sst = sst[:, order]

    # Latitudes descend from 89.5; ascend them so the grid is monotonic.
    if lat[0] > lat[-1]:
        lat = lat[::-1]
        sst = sst[::-1, :]

    return lon, lat, sst


def test_sat_ex1():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    lon, lat, sst = _load_sst()
    lon_g, lat_g = np.meshgrid(lon, lat)

    fig, ax = plt.subplots(figsize=(12, 6), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('hammer-aitoff', lon=CLON, lat=[-90, 90])

    # Leave the 'bad' colour transparent (the matplotlib default) so land shows
    # the figure background and is then covered by the coastline patch.
    cmap = plt.get_cmap('RdYlBu_r')

    vmin, vmax = SST_RANGE
    mm.m_pcolor(lon_g, lat_g, sst, cmap=cmap, vmin=vmin, vmax=vmax)

    mm.m_coast('patch', color=[0.6, 1.0, 0.6])
    mm.m_grid(xaxislocation='middle')

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=vmin, vmax=vmax))
    sm.set_array([])
    bar = fig.colorbar(sm, ax=ax, orientation='horizontal',
                       fraction=0.04, pad=0.04)
    bar.set_label('NOAA OI SST V2, November 1999 (°C)')

    out = OUTPUT_DIR / 'sat_ex1.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_sat_ex1()
