"""
Satellite Example 4 — NE Pacific SST anomaly ("the Blob"), Lambert conic.

This replaces an earlier version of this example that mapped *synthetic*
chlorophyll in place of the MODIS/SeaWiFS product used by map.html satellite
example 4.  No open, unauthenticated ocean-colour product was available to
substitute (NASA OB.DAAC now requires an Earthdata login), whereas the SST record
already fetched for satellite example 1 supports a more useful figure.

Where example 1 maps absolute SST globally, this maps a regional *anomaly* against
the record's own climatology — the standard way an ocean signal is presented, and a
different set of library features: a conic projection, a diverging colormap centred
on zero, and m_contfbar for the discrete bands.

The month shown is near the peak of the 2013-2015 NE Pacific marine heatwave, which
sat off the British Columbia coast and is the reason a generation of students has
heard of "the Blob".

Data
----
NOAA OI SST V2 monthly means (Reynolds et al., 2002), 1° global grid, downloaded
from NOAA PSL on first run and cached in ~/.py_m_map/ — see tests/example_data.py.
The climatology is computed from that same file over CLIM_YEARS, so the anomaly is
self-consistent and needs no second download.
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

TARGET_MONTH = '2015-01'
CLIM_YEARS = (1982, 2011)
LON_RANGE = (-160.0, -120.0)
LAT_RANGE = (32.0, 60.0)
LEVELS = np.arange(-3.0, 3.01, 0.5)


def _load_anomaly():
    """
    Monthly SST anomaly over the NE Pacific, against the CLIM_YEARS mean for the
    same calendar month.

    Returns
    -------
    lon, lat : 1-D arrays, ascending, degrees east on -180…180
    anomaly : 2-D (n_lat, n_lon), kelvin; NaN over land
    """
    (path,) = example_data.require('sst.mnmean.nc')
    cftime = xr.coders.CFDatetimeCoder(use_cftime=True)

    with xr.open_dataset(path, decode_times=cftime) as ds:
        sst = ds['sst']
        # Recentre 0.5…359.5 east onto -180…180 before selecting the region,
        # then re-sort so both coordinates are monotonic.
        sst = sst.assign_coords(lon=(((sst.lon + 180.0) % 360.0) - 180.0))
        sst = sst.sortby('lon').sortby('lat')
        sst = sst.sel(lon=slice(*LON_RANGE), lat=slice(*LAT_RANGE))

        target = sst.sel(time=TARGET_MONTH).squeeze()
        month = int(target.time.dt.month)

        years = sst.time.dt.year
        in_clim = (years >= CLIM_YEARS[0]) & (years <= CLIM_YEARS[1])
        climatology = sst.isel(
            time=(sst.time.dt.month == month) & in_clim
        ).mean('time')

        anomaly = target - climatology
        return (anomaly.lon.values.astype(float),
                anomaly.lat.values.astype(float),
                anomaly.values.astype(float))


def test_sat_ex4():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    lon, lat, anomaly = _load_anomaly()
    lon_g, lat_g = np.meshgrid(lon, lat)

    fig, ax = plt.subplots(figsize=(8, 7), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('lambert', lon=list(LON_RANGE), lat=list(LAT_RANGE))

    mm.m_contourf(lon_g, lat_g, anomaly, LEVELS,
                  cmap='RdBu_r', edgecolor='none', extend='both')

    mm.m_coast('patch', color=[0.75, 0.75, 0.72], edgecolor='k', linewidth=0.4)
    mm.m_grid(box='fancy', tickdir='out')

    # Below the frame, not inside it: an in-axes bar collides with the fancy box
    # and the longitude labels on a conic projection, whose corners reach low.
    cbar_ax, _ = mm.m_contfbar([0.25, 0.75], -0.10, anomaly, LEVELS,
                               axfrac=0.03, endpiece=True)
    cbar_ax.set_xlabel('SST anomaly (K)')

    # y above the default: a Lambert conic frame bulges upward in the middle, so
    # m_grid's fancy-box title offset still leaves the text touching the boundary.
    mm.m_title(f'NE Pacific SST anomaly, {TARGET_MONTH} '
               f'(vs {CLIM_YEARS[0]}–{CLIM_YEARS[1]})',
               y=1.06)

    out = OUTPUT_DIR / 'sat_ex4.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_sat_ex4()
