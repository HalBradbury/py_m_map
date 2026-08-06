"""
Satellite Example 6 — ARGO drifter tracks in the NE Pacific.

Mirrors the structure of map.html satellite example 6 but uses synthetic
ARGO float positions and displacements instead of real netCDF data files.

MATLAB equivalent (from map.html, satellite example 6):

    m_proj('lambert','lons',[-150 -124],'lat',[40 60],'rectbox','on');
    [cs,h]=m_etopo2('contourf',[-7000:500:0],'edgecolor','none');
    m_gshhs_l('patch',[.5 .8 0],'edgecolor','none');
    m_grid('linewi',2,'layer','top');
    caxis([-7000 000]);
    m_contfbar(.92,[.2 .5],cs,h,'endpiece','no','axfrac',.02);
    colormap(m_colmap('blue'));
    % Scale arrow
    m_vec(vecscl,-126,58,-0.01,0,'r','shaftwidth',2,'headlength',10,...
          'key',{'1 cm/s','Mean Drift'},'centered','yes');
    % Per-float: m_line, m_idist, m_fdist, m_vec

Notes
-----
* Twelve synthetic ARGO floats with realistic NE Pacific drift patterns.
* m_idist and m_fdist are used to compute the mid-point and direction of
  the net displacement between each float's first and last positions, exactly
  as in the MATLAB example.
* Blues colormap via m_colmap; depth contours via m_etopo2.
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

_LON_LIM = [-150.0, -124.0]
_LAT_LIM = [40.0, 60.0]


def _synthetic_argo_floats(n_floats: int = 12, n_steps: int = 20):
    """
    Generate synthetic ARGO float tracks.

    Returns a list of dicts with keys 'lon' (n_steps,) and 'lat' (n_steps,).
    """
    rng = np.random.default_rng(99)

    # Seed positions spread across NE Pacific
    seed_lons = rng.uniform(-148, -126, n_floats)
    seed_lats = rng.uniform(42, 58, n_floats)

    floats = []
    for k in range(n_floats):
        lons = [seed_lons[k]]
        lats = [seed_lats[k]]
        # Drift: general eastward / poleward North Pacific Current pattern
        for _ in range(n_steps - 1):
            # ~2 cm/s mean + random eddy noise
            u = 0.015 + 0.008 * rng.standard_normal()  # m/s eastward
            v = 0.003 + 0.005 * rng.standard_normal()  # m/s northward
            # 30-day timestep (approximately)
            dt = 30 * 86400  # seconds
            # Convert m/s → degrees
            dlat = np.rad2deg(v * dt / 6.371e6)
            dlon = np.rad2deg(u * dt / (6.371e6 * np.cos(np.deg2rad(lats[-1]))))
            lons.append(lons[-1] + dlon)
            lats.append(lats[-1] + dlat)
        floats.append({'lon': np.array(lons), 'lat': np.array(lats)})

    return floats


def test_sat_ex6():
    OUTPUT_DIR.mkdir(exist_ok=True)
    mm.reset_state()

    floats = _synthetic_argo_floats()

    fig, ax = plt.subplots(figsize=(10, 9), facecolor='white')
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('lambert', lon=_LON_LIM, lat=_LAT_LIM)

    # Bathymetry
    levels_depth = np.arange(-7000, 1, 500, dtype=float)
    depth_cmap = mm.m_colmap('blues', len(levels_depth) - 1)

    try:
        mm.m_etopo2('contourf', levels_depth, edgecolor='none',
                    cmap=depth_cmap, vmin=-7000, vmax=0)
    except Exception:
        mm.m_elev('contourf', levels_depth, edgecolor='none',
                  cmap=depth_cmap, vmin=-7000, vmax=0)

    # Coastlines — light green land fill
    mm.m_gshhs_l('patch', facecolor=[0.5, 0.8, 0.0], edgecolor='none')

    mm.m_grid(tickdir='out')

    # Depth colorbar, placed outside the frame (xpos > 1).  MATLAB puts it at
    # x=0.92, inside the axes, but this projection's right-hand boundary slants
    # across that column and the tick labels end up written over the frame.
    mm.m_contfbar(
        1.06, [0.15, 0.55],
        levels_depth.reshape(-1, 1), levels_depth,
        colormap=depth_cmap, caxis=(-7000, 0),
        axfrac=0.025, endpiece=False,
    )

    # Scale arrow: 1 cm/s at (−126°, 58°N)
    vec_scale = 0.015  # data units (m/s) per inch
    mm.m_vec(
        vec_scale, -126.0, 58.0, -0.01, 0.0, 'r',
        shaftwidth=2, headlength=10,
        key='1 cm/s',
        centered='yes',
    )

    # Draw each float track + net-displacement arrow
    Clon_list, Clat_list, spd_list, a21_list = [], [], [], []

    for flt in floats:
        lon_arr = flt['lon']
        lat_arr = flt['lat']

        # Clip to map bounds before drawing
        in_bounds = (
            (lon_arr >= _LON_LIM[0]) & (lon_arr <= _LON_LIM[1]) &
            (lat_arr >= _LAT_LIM[0]) & (lat_arr <= _LAT_LIM[1])
        )
        ii = np.where(in_bounds)[0]
        if len(ii) < 2:
            continue

        mm.m_line(lon_arr[ii], lat_arr[ii], color='k')

        # Use second and last valid positions (skip first — may be erroneous)
        i0, i1 = ii[1], ii[-1]
        dlon = lon_arr[[i0, i1]]
        dlat = lat_arr[[i0, i1]]
        dt_days = (i1 - i0) * 30.0  # days between the two endpoints

        dist_m, az12, _ = mm.m_idist(dlon[0], dlat[0], dlon[1], dlat[1])

        spd = dist_m / (dt_days * 86400.0)  # m/s

        # Mid-point on the geodesic
        clon, clat, az21 = mm.m_fdist(dlon[0], dlat[0], az12, dist_m / 2.0)
        clon = np.mod(clon - 360.0, 360.0) - 360.0  # keep west-of-prime

        Clon_list.append(float(clon))
        Clat_list.append(float(clat))
        spd_list.append(float(spd))
        a21_list.append(float(az21))

    if Clon_list:
        Clon = np.array(Clon_list)
        Clat = np.array(Clat_list)
        spd  = np.array(spd_list)
        a21  = np.array(a21_list)
        a21_back = np.mod(a21 - 180.0, 360.0)

        mm.m_vec(
            vec_scale,
            Clon, Clat,
            spd * np.sin(np.deg2rad(a21_back)),
            spd * np.cos(np.deg2rad(a21_back)),
            'r',
            centered='yes', shaftwidth=2, headlength=10,
        )

    out = OUTPUT_DIR / 'sat_ex6.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'\nSaved: {out}\n')


if __name__ == '__main__':
    test_sat_ex6()
