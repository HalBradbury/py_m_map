"""
Satellite Example 5 — NCEP Reanalysis surface winds and mean daily
precipitation rate, North Pacific, Miller projection.

Mirrors map.html satellite example 5 (Pawlowicz):

    m_proj('miller','lon',[100 260],'lat',[0 65]);
    m_coast('patch',[.8 .8 .8]);
    hold on
    [CS,CH]=m_contourf(LN,LT,prate'*1e3,[0.05:.05:.7],'edgecolor','none');
    m_windbarb(LN,LT,u',v',2,'units','m/s','linewi',1,'color','r');
    hold off;
    m_grid('box','fancy','tickdir','out');
    ax=m_contfbar([.3 .7],.05,CS,CH);
    xlabel(ax,'Mean Daily Precipitation Rate/(kg/m^2/s)');
    colormap(flipud(m_colmap('Blues')))
    title(['North Pacific Surface Winds : ...'])

Data (NCEP/NCAR Reanalysis 1, T62 Gaussian grid 192×94), downloaded from NOAA PSL
on first run and cached in ~/.py_m_map/ — see tests/example_data.py:
    prate.sfc.mon.ltm.1991-2020.nc     January climatology, kg m⁻² s⁻¹
    uwnd/vwnd.10m.mon.ltm.1991-2020.nc January climatology, m s⁻¹

The 1991–2020 long-term-mean (LTM) files are used rather than averaging the full
monthly series: they are the same climatology (verified bit-identical for January)
in 1.2 MB instead of a multi-decade time series.
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

_JANUARY = 0        # time index into the 12-month climatology
_LAT = slice(0, 65)
_LON = slice(100, 260)


def _load_data():
    """
    January climatological precipitation rate and 10 m winds over the North
    Pacific, on the native T62 Gaussian grid.

    Returns
    -------
    lon, lat : 1-D arrays  (ascending)
    prate_scaled : 2-D (n_lat, n_lon)  — prate × 1000, shape matches meshgrid
    u_ms, v_ms : 2-D (n_lat, n_lon)   — 10 m winds, m s⁻¹
    """
    prate_file, u_file, v_file = example_data.require(
        'prate.sfc.mon.ltm.1991-2020.nc',
        'uwnd.10m.mon.ltm.1991-2020.nc',
        'vwnd.10m.mon.ltm.1991-2020.nc',
    )
    cftime = xr.coders.CFDatetimeCoder(use_cftime=True)

    def _january(path, name):
        with xr.open_dataset(path, decode_times=cftime) as ds:
            field = (ds[name]
                     .isel(time=_JANUARY)
                     .sortby('lat')
                     .sel(lat=_LAT, lon=_LON))
            return (field.lon.values.astype(float),
                    field.lat.values.astype(float),
                    field.values.astype(float))

    lon, lat, prate = _january(prate_file, 'prate')
    _, _, u_ms = _january(u_file, 'uwnd')
    _, _, v_ms = _january(v_file, 'vwnd')

    return lon, lat, prate * 1e3, u_ms, v_ms


def test_sat_ex5():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    lon, lat, prate_scaled, u_ms, v_ms = _load_data()
    lon_g, lat_g = np.meshgrid(lon, lat)

    prate_levels = np.arange(0.05, 0.2, 0.01)
    n_bands = len(prate_levels) - 1
    # Clip Blues to [0.2, 1.0] so the lightest band is a visible pale blue,
    # not near-white against the white ocean background.
    blues_cmap = mcolors.ListedColormap(
        plt.cm.Blues(np.linspace(0.2, 1.0, n_bands))[:, :3]
    )

    fig, ax = plt.subplots(figsize=(11, 6), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('miller', lon=[100, 260], lat=[0, 65])

    # Coast first (drawn beneath contourf and wind barbs)
    mm.m_coast('patch', color=[0.8, 0.8, 0.8], edgecolor='none')

    # Precipitation filled contours
    mm.m_contourf(lon_g, lat_g, prate_scaled, prate_levels,
                  cmap=blues_cmap, edgecolor='none')

    # Wind barbs — red, slightly smaller than MATLAB's scale=2
    mm.m_windbarb(lon_g, lat_g, u_ms, v_ms,
                  scale=0.7, units='m/s',
                  color='r', linewidth=0.8, zorder=5)

    mm.m_grid(box='fancy', boxstyle='line', tickdir='out')

    cbar_ax, _ = mm.m_contfbar([0.3, 0.7], -0.12, prate_scaled, prate_levels,
                                endpiece=True, extend='both')
    cbar_ax.set_xlabel('Mean Daily Precipitation Rate / (kg m$^{-2}$ s$^{-1}$)')

    mm.m_title('North Pacific Surface Winds')

    out = OUTPUT_DIR / 'sat_ex5.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_sat_ex5()
