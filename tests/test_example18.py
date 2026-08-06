"""
Example 18 — Shaded Relief (Example 2) — Vancouver Harbour with UTM grid.

Mirrors the structure of map.html example 18.  Primary data source is the
seamless WEST_COAST_DEM raster embedded in canada_west_coast_DEM_original.gdb
(NAD83 / BC Albers, 10-m, EPSG:3005), which is reprojected to geographic
coordinates on load.  Falls back to NONNA10 GeoTIFF tiles if the GDB is
unavailable, and to synthetic data if both are absent.

Coastline polygons are derived from the WEST_COAST_DEM_SOURCE_MAP vector layer
in the same GDB.

MATLAB equivalent (from map.html, example 18):

    m_proj('utm','ellipse','grs80','zone',10,...
           'lat',[49+15.7/60 49+21/60],'long',[-123-15/60 -123-3/60]);
    m_shadedrelief(x2,y2,-Z2,'lightangle',-45,'gradient',8,'coord','z');
    col=[255 214 140]/255;  % CHS chart land colour
    m_usercoast('PNW.mat','patch',col);
    m_grid('tickdir','out','linest','none','xaxisloc','top','yaxisloc','right');
    m_utmgrid('xcolor','b','ycolor','b','linest','-');
    m_ruler([.5 .8],.9,'tickdir','out');
    m_northarrow(-123-4.5/60,49+19.5/60,1/60,'type',4,'aspect',1.5);
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

# Vancouver Harbour extent (MATLAB example)
_LON_LIM = [-(123 + 15 / 60), -(123 + 3 / 60)]   # ≈ [-123.250, -123.050]
_LAT_LIM = [49 + 15.7 / 60,   49 + 21 / 60]       # ≈ [49.262,  49.350]

_DATABASES = Path(__file__).parent.parent.parent / 'databases'
_GDB_PATH  = _DATABASES / 'canada_west_coast_DEM_original.gdb'
_NHN_GDB   = _DATABASES / 'nhn_rhn_08gabx1_gdb_en' / 'NHN_08GABX1_2_0.gdb'
_NONNA10_TILES = [
    'NONNA10_4920N12310W.tiff',
    'NONNA10_4920N12320W.tiff',
    'NONNA10_4920N12330W.tiff',
    'NONNA10_4930N12310W.tiff',
    'NONNA10_4930N12320W.tiff',
    'NONNA10_4930N12330W.tiff',
]

# ---------------------------------------------------------------------------
# Bathymetry loaders
# ---------------------------------------------------------------------------

def _load_gdb_dem():
    """
    Read the WEST_COAST_DEM raster from the GDB (NAD83 / BC Albers, 10-m),
    warp the Vancouver Harbour window to EPSG:4326, and return
    (lon_vec, lat_vec, Z).  Z is (nlat, nlon) in metres; no NaN gaps.
    """
    from osgeo import gdal
    gdal.UseExceptions()

    margin = 0.01  # degrees
    sub = (
        f'OpenFileGDB:"{_GDB_PATH}":WEST_COAST_DEM'
    )
    warp_opts = gdal.WarpOptions(
        format='MEM',
        dstSRS='EPSG:4326',
        outputBounds=(
            _LON_LIM[0] - margin, _LAT_LIM[0] - margin,
            _LON_LIM[1] + margin, _LAT_LIM[1] + margin,
        ),
        xRes=0.0001, yRes=0.0001,
        resampleAlg=gdal.GRA_Bilinear,
    )
    warped = gdal.Warp('', sub, options=warp_opts)
    gt = warped.GetGeoTransform()
    band = warped.GetRasterBand(1)
    Z = band.ReadAsArray().astype(float)
    nodata = band.GetNoDataValue()
    if nodata is not None:
        Z[Z == nodata] = np.nan
    nrows, ncols = Z.shape
    lon_vec = gt[0] + (np.arange(ncols) + 0.5) * gt[1]
    lat_vec = gt[3] + (np.arange(nrows) + 0.5) * gt[5]
    warped = None
    if lat_vec[0] > lat_vec[-1]:
        lat_vec = lat_vec[::-1]
        Z = Z[::-1, :]
    return lon_vec, lat_vec, Z


def _load_nonna10():
    """
    Mosaic the NONNA10 tiles that cover Vancouver Harbour and return
    (lon_vec, lat_vec, Z) clipped to _LON_LIM / _LAT_LIM.

    Z is (nlat, nlon) in metres; NaN where no survey data.
    """
    import rasterio
    from rasterio.merge import merge

    tile_paths = [_DATABASES / t for t in _NONNA10_TILES]
    datasets = [rasterio.open(p) for p in tile_paths]
    nodata_val = datasets[0].nodata

    mosaic, transform = merge(datasets)
    for ds in datasets:
        ds.close()

    Z = mosaic[0].astype(float)
    Z[Z == nodata_val] = np.nan

    nrows, ncols = Z.shape
    lon_vec = transform.c + (np.arange(ncols) + 0.5) * transform.a
    lat_vec = transform.f + (np.arange(nrows) + 0.5) * transform.e

    margin = 0.005
    lon_mask = (lon_vec >= _LON_LIM[0] - margin) & (lon_vec <= _LON_LIM[1] + margin)
    lat_mask = (lat_vec >= _LAT_LIM[0] - margin) & (lat_vec <= _LAT_LIM[1] + margin)
    lon_vec = lon_vec[lon_mask]
    lat_vec = lat_vec[lat_mask]
    Z = Z[np.ix_(lat_mask, lon_mask)]

    if lat_vec[0] > lat_vec[-1]:
        lat_vec = lat_vec[::-1]
        Z = Z[::-1, :]

    return lon_vec, lat_vec, Z


def _synthetic_harbour_bathy(nlon: int = 120, nlat: int = 90):
    """Synthetic Vancouver Harbour scene — fallback when no real data available."""
    rng = np.random.default_rng(42)
    lon_vec = np.linspace(_LON_LIM[0], _LON_LIM[1], nlon)
    lat_vec = np.linspace(_LAT_LIM[0], _LAT_LIM[1], nlat)
    lon_g, lat_g = np.meshgrid(lon_vec, lat_vec)
    lon_c, lat_c = np.mean(_LON_LIM), np.mean(_LAT_LIM)
    dlat = _LAT_LIM[1] - _LAT_LIM[0]
    dlon = _LON_LIM[1] - _LON_LIM[0]
    dist = np.hypot((lon_g - lon_c) / dlon, (lat_g - lat_c) / dlat)
    Z = -80.0 * (1.0 - 2.2 * dist) + 5.0 * rng.standard_normal(lon_g.shape)
    Z = np.clip(Z, -100.0, 30.0)
    land_mask = dist > 0.45
    Z[land_mask] += 15.0 * dist[land_mask]
    return lon_vec, lat_vec, Z


def _get_bathy():
    """Return (lon_vec, lat_vec, Z).  Tries GDB DEM → NONNA10 tiles → synthetic."""
    if _GDB_PATH.exists():
        try:
            return _load_gdb_dem(), 'GDB seamless DEM'
        except Exception as exc:
            print(f'Warning: GDB DEM load failed ({exc}); trying NONNA10 tiles.')
    tiles_present = all((_DATABASES / t).exists() for t in _NONNA10_TILES)
    if tiles_present:
        try:
            return _load_nonna10(), 'NONNA10 tiles'
        except Exception as exc:
            print(f'Warning: NONNA10 load failed ({exc}); using synthetic data.')
    return _synthetic_harbour_bathy(), 'synthetic'


# ---------------------------------------------------------------------------
# River loader (NHN)
# ---------------------------------------------------------------------------

def _load_nhn_rivers():
    """
    Load watercourse centrelines from the NHN GDB for the Vancouver Harbour
    bounding box.  Returns a list of (lon_arr, lat_arr) pairs (NaN-separated)
    ready for projection and plotting.
    """
    from osgeo import ogr
    ogr.UseExceptions()

    ds = ogr.Open(str(_NHN_GDB))
    lyr = ds.GetLayerByName('NHN_HN_NLFLOW_1')
    margin = 0.01
    lyr.SetSpatialFilterRect(
        _LON_LIM[0] - margin, _LAT_LIM[0] - margin,
        _LON_LIM[1] + margin, _LAT_LIM[1] + margin,
    )

    seg_lons, seg_lats = [], []
    for feat in lyr:
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        # Flatten MULTILINESTRING → individual line strings
        if geom.GetGeometryCount() > 0:
            parts = [geom.GetGeometryRef(i) for i in range(geom.GetGeometryCount())]
        else:
            parts = [geom]
        for part in parts:
            pts = part.GetPoints()
            if not pts:
                continue
            lons = [p[0] for p in pts]
            lats = [p[1] for p in pts]
            seg_lons.extend(lons + [np.nan])
            seg_lats.extend(lats + [np.nan])

    ds = None
    if not seg_lons:
        return []
    return [(np.array(seg_lons), np.array(seg_lats))]


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

def _draw_dem_coastline(ax, lon_vec, lat_vec, Z):
    """Fill land (Z ≥ 0) using the DEM; the Z=0 contour forms the shoreline."""
    col = [255 / 255, 214 / 255, 140 / 255]
    x_map, _ = mm.m_ll2xy(lon_vec, np.full(len(lon_vec), lat_vec.mean()), clip='off')
    _, y_map = mm.m_ll2xy(np.full(len(lat_vec), lon_vec.mean()), lat_vec, clip='off')
    XX, YY = np.meshgrid(x_map, y_map)
    zmax = float(np.nanmax(Z))
    ax.contourf(XX, YY, Z, levels=[0.0, zmax], colors=[col])
    ax.contour(XX, YY, Z, levels=[0.0], colors=['k'], linewidths=0.5)


def _draw_panel(ax, lon_vec, lat_vec, Z, nan_color, label, source_name,
                coast_lon=None, coast_lat=None, coast_Z=None, rivers=None):
    """Render one Vancouver Harbour panel onto ax."""
    mm.reset_state()
    ax.set_facecolor('white')
    plt.sca(ax)

    mm.m_proj('utm', lat=_LAT_LIM, lon=_LON_LIM)

    blues_rgb = mm.m_colmap('water', 128)
    mm.m_shadedrelief(lon_vec, lat_vec, Z,
                      coords='geog', light_angle=-45, gradient=8,
                      colormap=blues_rgb, caxis=(-80, 0),
                      nan_color=nan_color)

    contour_levels = [-75, -50, -30, -20, -10, -5]
    cs = mm.m_contour(lon_vec, lat_vec, Z, levels=contour_levels,
                      colors='k', linewidths=0.4, alpha=0.6)
    ax.clabel(cs, fmt='%d m', fontsize=5, inline=True)

    col = [255 / 255, 214 / 255, 140 / 255]   # CHS chart land colour
    if coast_Z is not None:
        _draw_dem_coastline(ax, coast_lon, coast_lat, coast_Z)
    else:
        mm.m_gshhs_f('patch', col, edgecolor='k', linewidth=0.5)

    mm.m_grid(tickdir='out', linestyle='none',
              xaxislocation='top', yaxislocation='right')
    mm.m_utmgrid(color='b', linestyle='-')

    if rivers is not None:
        for seg_lons, seg_lats in rivers:
            valid = ~(np.isnan(seg_lons) | np.isnan(seg_lats))
            rx = np.full_like(seg_lons, np.nan)
            ry = np.full_like(seg_lats, np.nan)
            if valid.any():
                rx[valid], ry[valid] = mm.m_ll2xy(
                    seg_lons[valid], seg_lats[valid], clip='off')
            ax.plot(rx, ry, color='steelblue', linewidth=0.8, clip_on=True)

    mm.m_ruler([0.5, 0.78], 0.9)
    mm.m_northarrow(-(123 + 4.5 / 60), 49 + 19.5 / 60, 1 / 60,
                    type=4, aspect=1.5)

    ax.text(0.02, 0.98, f'\u2003{label}\u2003{source_name}',
            transform=ax.transAxes, fontsize=7,
            fontweight='bold', va='top', ha='left',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.7, pad=1.5))


def test_example18():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load NONNA10 tiles (with NaN survey gaps)
    tiles_present = all((_DATABASES / t).exists() for t in _NONNA10_TILES)
    if tiles_present:
        try:
            lon_n, lat_n, Z_n = _load_nonna10()
            nonna_label = 'NONNA10 tiles'
        except Exception as exc:
            print(f'Warning: NONNA10 load failed ({exc}); using synthetic.')
            lon_n, lat_n, Z_n = _synthetic_harbour_bathy()
            nonna_label = 'synthetic'
    else:
        lon_n, lat_n, Z_n = _synthetic_harbour_bathy()
        nonna_label = 'synthetic'

    # Load GDB seamless DEM (gap-free)
    if _GDB_PATH.exists():
        try:
            lon_g, lat_g, Z_g = _load_gdb_dem()
            gdb_label = 'GDB seamless DEM'
        except Exception as exc:
            print(f'Warning: GDB DEM load failed ({exc}); using synthetic.')
            lon_g, lat_g, Z_g = _synthetic_harbour_bathy()
            gdb_label = 'synthetic'
    else:
        lon_g, lat_g, Z_g = _synthetic_harbour_bathy()
        gdb_label = 'synthetic'

    rivers = None
    if _NHN_GDB.exists():
        try:
            rivers = _load_nhn_rivers()
            npts = sum(len(s[0]) for s in rivers)
            print(f'Rivers: {npts} points loaded from NHN GDB')
        except Exception as exc:
            print(f'Warning: NHN river load failed ({exc})')

    print(f'\nNONNA10 : {nonna_label}  grid {len(lon_n)} × {len(lat_n)}'
          f'  Z [{np.nanmin(Z_n):.1f}, {np.nanmax(Z_n):.1f}] m'
          f'  NaN {np.isnan(Z_n).mean():.1%}')
    print(f'GDB DEM : {gdb_label}  grid {len(lon_g)} × {len(lat_g)}'
          f'  Z [{np.nanmin(Z_g):.1f}, {np.nanmax(Z_g):.1f}] m'
          f'  NaN {np.isnan(Z_g).mean():.1%}')
    # Use the seamless GDB DEM for the coastline on both panels (0% NaN,
    # accurate Z=0 shoreline that correctly resolves False Creek).
    coast = (lon_g, lat_g, Z_g) if gdb_label != 'synthetic' else (None, None, None)

    fig, axes = plt.subplots(1, 2, figsize=(18, 8), facecolor='white')

    _draw_panel(axes[0], lon_n, lat_n, Z_n,
                nan_color=(0.85, 0.92, 0.97), label='A', source_name=nonna_label,
                coast_lon=coast[0], coast_lat=coast[1], coast_Z=coast[2],
                rivers=rivers)
    _draw_panel(axes[1], lon_g, lat_g, Z_g,
                nan_color=(1.0, 1.0, 1.0), label='B', source_name=gdb_label,
                coast_lon=coast[0], coast_lat=coast[1], coast_Z=coast[2],
                rivers=rivers)

    fig.tight_layout()
    out = OUTPUT_DIR / 'example18.png'
    fig.savefig(str(out), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'Saved: {out}\n')


if __name__ == '__main__':
    test_example18()
