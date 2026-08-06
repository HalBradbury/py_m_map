"""
High-resolution ETOPO1 topography / bathymetry reader.

m_etopo2 — ported from m_etopo2.m (R. Pawlowicz)

Reads the 1-arc-minute ETOPO1 binary file etopo1_ice_g_i2.bin.
Falls back to m_elev (1-degree database) if the binary is not found.

Database file
-------------
etopo1_ice_g_i2.bin  (little-endian int16, grid-referenced, ~447 MB)
Download from:
  https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/ice_surface/
      grid_registered/binary/etopo1_ice_g_i2.zip
Place the unzipped file in the shared databases folder:
  ../databases/etopo1_ice_g_i2.bin   (relative to the py_m_map package root)
"""
from __future__ import annotations
import os
import warnings
import numpy as np

from ._data import ENV_VAR, missing_data_message, resolve_data_file

_ETOPO1_NAME = 'etopo1_ice_g_i2.bin'
# Legacy location: a shared databases/ folder beside this project's parent.
_ETOPO1_PACKAGE_RELATIVE = ('..', '..', 'databases')
_DOWNLOAD_HINT = (
    'Download etopo1_ice_g_i2.zip (~447 MB) from https://www.ngdc.noaa.gov/mgg/'
    'global/relief/ETOPO1/data/ice_surface/grid_registered/binary/ and unzip it.'
)


def _etopo1_path():
    """Current ETOPO1 location, or None.  Resolved per call so that setting
    PY_M_MAP_DATA_DIR mid-session takes effect."""
    return resolve_data_file(_ETOPO1_NAME, _ETOPO1_PACKAGE_RELATIVE)

# ETOPO1 grid constants (grid-referenced, 1 arc-minute)
_RESOLUTION = 1          # arc-minutes per cell
_PTSPERDEG  = 60         # = 60 / resolution
_NX         = 21600      # 360° × 60 pts/deg
_NY         = 10800      # 180° × 60 pts/deg
_PTSPERLINE = _NX + 1    # grid-referenced: one extra point per row
_DECMAX     = 800        # max points per axis before decimation


def _read_etopo1_region(
    lon_min: float, lon_max: float,
    lat_min: float, lat_max: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract a lon/lat sub-region from the ETOPO1 binary.

    Returns
    -------
    lons : 1-D array, ascending, decimal degrees
    lats : 1-D array, ascending, decimal degrees
    Z    : 2-D array, shape (len(lats), len(lons)), metres
    """
    # Expand by 1 arc-minute on each side so contours reach map edges
    pad = 1.0 / _PTSPERDEG

    # Column indices (0 = lon –180°)
    llong = int(np.floor((lon_min - pad) * _PTSPERDEG))
    rlong = int(np.ceil( (lon_max + pad) * _PTSPERDEG))

    # Row indices counted from equator (positive = north)
    blat  = int(np.floor((lat_min - pad) * _PTSPERDEG))
    tlat  = int(np.ceil( (lat_max + pad) * _PTSPERDEG))

    # Convert to file-space indices (origin at lon=-180°, lat=+90°)
    # col_start/col_end: column index from the left edge of the file
    col_start = llong + _NX // 2      # _NX//2 = 10800 offsets -180° → 0
    col_end   = rlong + _NX // 2

    # row_start/row_end: row index from the top (north pole = row 0)
    row_start = _NY // 2 - tlat       # northern edge → smaller row number
    row_end   = _NY // 2 - blat       # southern edge → larger row number

    # Detect an antimeridian crossing BEFORE wrapping.  The modulo below maps
    # both indices into [0, _NX), so testing col_end > _NX afterwards can never
    # succeed — and col_end would wrap below col_start, giving a negative width.
    straddles = col_end > _NX

    # Wrap the start index into the valid range.  col_end is left unwrapped when
    # the region straddles, so the two-piece read below can size its halves.
    col_start %= _NX
    if not straddles:
        col_end %= _NX

    nlat = row_end   - row_start + 1
    nlng = col_end   - col_start + 1

    # Decimation so we never load more than DECMAX²-ish points
    lngdec = max(1, int(np.ceil(nlng / _DECMAX)))
    latdec = max(1, int(np.ceil(nlat / _DECMAX)))

    etopo1_file = _etopo1_path()
    if etopo1_file is None:
        raise FileNotFoundError(missing_data_message(
            _ETOPO1_NAME, what='m_etopo2',
            download_hint=_DOWNLOAD_HINT,
            package_relative=_ETOPO1_PACKAGE_RELATIVE,
        ))

    with open(etopo1_file, 'rb') as fid:
        if straddles:
            # Straddles the antimeridian — read in two pieces
            nlgr = col_end   - _NX + 1   # right piece (east of antimeridian)
            nlgl = _NX - col_start        # left piece  (west of antimeridian)
            values = np.empty((nlat, nlgr + nlgl), dtype=np.int16)
            for ii in range(nlat):
                # Right piece (columns 0 … nlgr-1 of file)
                offset = int(((ii + row_start) * _PTSPERLINE) * 2)
                fid.seek(offset)
                values[ii, nlgl:] = np.frombuffer(fid.read(nlgr * 2), dtype='<i2')
                # Left piece (columns col_start … NX-1 of file)
                offset = int(((ii + row_start) * _PTSPERLINE + col_start) * 2)
                fid.seek(offset)
                values[ii, :nlgl] = np.frombuffer(fid.read(nlgl * 2), dtype='<i2')
        else:
            # Contiguous region — read one row at a time
            values = np.empty((nlat, nlng), dtype=np.int16)
            for ii in range(nlat):
                offset = int(((ii + row_start) * _PTSPERLINE + col_start) * 2)
                fid.seek(offset)
                values[ii, :] = np.frombuffer(fid.read(nlng * 2), dtype='<i2')

    # Decimate
    values = values[::latdec, ::lngdec].astype(float)

    # Coordinate arrays
    # MATLAB: lgs = [llong:rlong]/ptsperdeg  (ascending lon)
    #         lts = fliplr([blat:tlat]/ptsperdeg)  (descending lat → N-first)
    # We build ascending lat array (S→N) to match m_elev convention.
    lons_full = np.arange(llong, rlong + 1) / float(_PTSPERDEG)
    lats_full = np.arange(blat,  tlat  + 1) / float(_PTSPERDEG)

    lons = lons_full[::lngdec]
    lats = lats_full[::latdec]

    # File rows are north→south; flip data rows to match ascending lats (south→north).
    # lats_full is already ascending — do NOT flip it.
    values = values[::-1, :]

    # Trim to actual array size (decimation may leave 1 extra point)
    lons = lons[:values.shape[1]]
    lats = lats[:values.shape[0]]

    return lons, lats, values


def m_etopo2(
    mode: str = 'contourf',
    levels=None,
    **kwargs,
):
    """
    Draw topography / bathymetry from the ETOPO1 1-arc-minute database.

    Falls back to m_elev (1-degree database) if the binary is not installed.

    Parameters
    ----------
    mode : {'contourf', 'contour', 'shadedrelief'}
        Type of plot.
    levels : array-like or None
        Contour levels.  Default: 1000 m intervals from −7000 to +5000 m.
    **kwargs
        Forwarded to the underlying plotting function.

    Returns
    -------
    The return value of the underlying plotting function.
    """
    from ._state import get_state
    from .contour import m_contourf, m_contour

    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    if _etopo1_path() is None:
        warnings.warn(
            missing_data_message(
                _ETOPO1_NAME, what='m_etopo2',
                download_hint=_DOWNLOAD_HINT,
                package_relative=_ETOPO1_PACKAGE_RELATIVE,
            )
            + '\n  Falling back to the 1-degree m_elev database for now.',
            stacklevel=2,
        )
        from .elevation import m_elev
        return m_elev(mode=mode, levels=levels, **kwargs)

    lons, lats, Z = _read_etopo1_region(
        state.lon_limits[0], state.lon_limits[1],
        state.lat_limits[0], state.lat_limits[1],
    )

    if levels is None:
        levels = np.concatenate([
            np.arange(-7000, -999, 1000),
            np.arange(1000, 5001, 1000),
        ])
    else:
        levels = np.asarray(levels, dtype=float)

    if mode == 'contourf':
        return m_contourf(lons, lats, Z, levels, **kwargs)
    elif mode == 'contour':
        return m_contour(lons, lats, Z, levels, **kwargs)
    elif mode == 'shadedrelief':
        from .shaded_relief import m_shadedrelief
        return m_shadedrelief(lons, lats, Z, **kwargs)
    else:
        raise ValueError(f"m_etopo2: unrecognised mode '{mode}'.")
