"""
Real datasets used by the example figures, fetched on demand and cached.

Every source here is open NOAA data needing no authentication, so the examples
are reproducible by anyone who runs them.  Files land in ``~/.py_m_map/`` (or
anywhere on the ``PY_M_MAP_DATA_DIR`` search path) and are downloaded once.

The two OISST files are 64 MB each.  Examples that need them are skipped unless
the file is already cached or ``PY_M_MAP_FETCH_LARGE=1`` is set, so a routine
``pytest`` run stays light while still exercising them once the data is present.

Provenance
----------
NCEP/NCAR Reanalysis 1 — Kalnay et al. (1996), NOAA PSL.
NOAA OI SST V2 — Reynolds et al. (2002), NOAA PSL.
Both are US Government works, distributed from https://psl.noaa.gov/data/
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from py_m_map._data import (  # noqa: E402
    DataFetchError,
    fetch_data_file,
    resolve_data_file,
)

_PSL = 'https://downloads.psl.noaa.gov/Datasets'
_NCEP_GAUSS = f'{_PSL}/ncep.reanalysis.derived/surface_gauss'
_OISST = f'{_PSL}/noaa.oisst.v2'

#: name -> (url, human description, is_large)
DATASETS: dict[str, tuple[str, str, bool]] = {
    'prate.sfc.mon.ltm.1991-2020.nc': (
        f'{_NCEP_GAUSS}/prate.sfc.mon.ltm.1991-2020.nc',
        'NCEP reanalysis precipitation rate climatology (1.2 MB)',
        False,
    ),
    'uwnd.10m.mon.ltm.1991-2020.nc': (
        f'{_NCEP_GAUSS}/uwnd.10m.mon.ltm.1991-2020.nc',
        'NCEP reanalysis 10 m zonal wind climatology (1.2 MB)',
        False,
    ),
    'vwnd.10m.mon.ltm.1991-2020.nc': (
        f'{_NCEP_GAUSS}/vwnd.10m.mon.ltm.1991-2020.nc',
        'NCEP reanalysis 10 m meridional wind climatology (1.2 MB)',
        False,
    ),
    'sst.mnmean.nc': (
        f'{_OISST}/sst.mnmean.nc',
        'NOAA OI SST V2 monthly means (64 MB)',
        True,
    ),
    'icec.mnmean.nc': (
        f'{_OISST}/icec.mnmean.nc',
        'NOAA OI SST V2 monthly sea-ice concentration (64 MB)',
        True,
    ),
}

FETCH_LARGE = os.environ.get('PY_M_MAP_FETCH_LARGE', '') not in ('', '0')


def dataset_path(name: str) -> Path:
    """
    Local path to a named dataset, fetching it if needed.

    Raises DataFetchError if unavailable — callers in tests should use
    :func:`require` instead so the test skips rather than fails.
    """
    try:
        url, description, is_large = DATASETS[name]
    except KeyError:
        raise KeyError(
            f'unknown example dataset {name!r}; known: {sorted(DATASETS)}'
        ) from None

    cached = resolve_data_file(name)
    if cached is not None:
        return cached

    if is_large and not FETCH_LARGE:
        raise DataFetchError(
            f'{description} is not cached, and large downloads are opt-in.\n'
            f'  Run once with PY_M_MAP_FETCH_LARGE=1 to fetch it, or download\n'
            f'  {url}\n  into ~/.py_m_map/'
        )

    return fetch_data_file(name, url, description=description)


def require(*names: str) -> list[Path]:
    """
    Paths for the named datasets, skipping the test if any is unavailable.

    Keeps the suite green offline and on a cold cache, while still failing loudly
    on a genuine error once the data is present.
    """
    paths = []
    for name in names:
        try:
            paths.append(dataset_path(name))
        except DataFetchError as exc:
            pytest.skip(f'example data unavailable: {exc}')
    return paths
