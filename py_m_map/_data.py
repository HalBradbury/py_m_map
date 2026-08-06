"""
Locating the external data files the elevation functions need.

Two data sets are too large, or too encumbered, to ship inside the wheel:

``m_topo.mat``
    The 1°×1° global topography that backs :func:`py_m_map.m_elev`.  It is part
    of the MATLAB m_map distribution.
``etopo1_ice_g_i2.bin``
    The 1 arc-minute ETOPO1 ice-surface grid (~447 MB) that backs
    :func:`py_m_map.m_etopo2`.  Download from
    https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/ice_surface/grid_registered/binary/

Both were previously found through a path relative to the package directory,
which only works from a source checkout laid out beside a MATLAB m_map install.
Once installed into site-packages those paths point nowhere, so the functions
failed for every user who did not happen to reproduce the author's directory
layout.  :func:`resolve_data_file` searches, in order:

1. ``$PY_M_MAP_DATA_DIR`` — a directory (or ``os.pathsep``-separated list) given
   explicitly by the user.  Checked first so it always wins.
2. ``~/.py_m_map/`` — the conventional per-user location.
3. Paths relative to the package, preserving the original source-checkout
   layout so an existing working setup keeps working.

Each candidate is tried both directly and inside a subdirectory named after the
file's stem, since the ETOPO1 download unpacks into its own folder.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = 'PY_M_MAP_DATA_DIR'

#: Per-user data directory searched after the environment variable.
USER_DATA_DIR = Path.home() / '.py_m_map'


def _env_dirs() -> list[Path]:
    raw = os.environ.get(ENV_VAR, '')
    return [Path(p).expanduser() for p in raw.split(os.pathsep) if p]


def candidate_paths(filename: str, package_relative: tuple[str, ...] = ()) -> list[Path]:
    """
    Every location that will be searched for `filename`, in priority order.

    `package_relative` holds legacy paths relative to the package directory,
    e.g. ``('..', '..', 'databases')``.
    """
    here = Path(__file__).resolve().parent
    roots: list[Path] = [*_env_dirs(), USER_DATA_DIR]
    if package_relative:
        roots.append((here / Path(*package_relative)).resolve())

    stem = Path(filename).stem
    out: list[Path] = []
    for root in roots:
        out.append(root / filename)
        out.append(root / stem / filename)   # e.g. databases/etopo1_.../etopo1_....bin
    return out


def resolve_data_file(
    filename: str,
    package_relative: tuple[str, ...] = (),
) -> Path | None:
    """Return the first existing candidate for `filename`, or None."""
    for path in candidate_paths(filename, package_relative):
        if path.is_file():
            return path
    return None


class DataFetchError(RuntimeError):
    """A required data file was absent and could not be downloaded."""


def fetch_data_file(
    filename: str,
    url: str,
    *,
    description: str | None = None,
    package_relative: tuple[str, ...] = (),
    quiet: bool = False,
) -> Path:
    """
    Return a local path to `filename`, downloading it into the cache if absent.

    Search order is the same as :func:`resolve_data_file`, so a file the user has
    already placed anywhere on the search path is used as-is and nothing is
    fetched.  Otherwise it is streamed to :data:`USER_DATA_DIR`.

    The download goes to a ``.part`` file and is renamed into place only on
    success, so an interrupted transfer cannot leave a truncated file that later
    looks valid.

    Set ``PY_M_MAP_NO_DOWNLOAD=1`` to forbid network access; the call then raises
    :class:`DataFetchError` naming every location searched.

    Raises
    ------
    DataFetchError
        If the file is absent and cannot be downloaded.
    """
    import shutil
    import sys
    import urllib.error
    import urllib.request

    existing = resolve_data_file(filename, package_relative)
    if existing is not None:
        return existing

    label = description or filename

    if _downloads_disabled():
        raise DataFetchError(
            f"{label} is not available locally and downloads are disabled "
            f"(PY_M_MAP_NO_DOWNLOAD is set).\n"
            f"  Download it yourself from:\n    {url}\n"
            f"  and place it in {USER_DATA_DIR}/ (or any directory named in "
            f"{ENV_VAR})."
        )

    target = USER_DATA_DIR / filename
    partial = target.with_name(target.name + '.part')
    target.parent.mkdir(parents=True, exist_ok=True)

    if not quiet:
        print(f'py_m_map: downloading {label}\n  from {url}\n  to   {target}',
              file=sys.stderr, flush=True)

    try:
        request = urllib.request.Request(
            url, headers={'User-Agent': 'py_m_map'}
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            total = response.headers.get('Content-Length')
            total = int(total) if total else None
            done = 0
            step = 8 * 1024 * 1024        # progress line every 8 MB
            next_report = step
            with open(partial, 'wb') as handle:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    handle.write(chunk)
                    done += len(chunk)
                    if not quiet and done >= next_report:
                        pct = f' ({100 * done / total:.0f} %)' if total else ''
                        print(f'  {done / 1e6:.0f} MB{pct}', file=sys.stderr,
                              flush=True)
                        next_report += step
        if total is not None and done != total:
            raise DataFetchError(
                f'{label}: transfer incomplete ({done} of {total} bytes).'
            )
        shutil.move(str(partial), str(target))
    except DataFetchError:
        partial.unlink(missing_ok=True)
        raise
    except (urllib.error.URLError, OSError) as exc:
        partial.unlink(missing_ok=True)
        raise DataFetchError(
            f'{label} could not be downloaded: {type(exc).__name__}: {exc}\n'
            f'  Tried: {url}\n'
            f'  Download it manually and place it in {USER_DATA_DIR}/, '
            f'or set {ENV_VAR} to a directory containing it.'
        ) from exc

    if not quiet:
        print(f'  done ({target.stat().st_size / 1e6:.0f} MB)',
              file=sys.stderr, flush=True)
    return target


def _downloads_disabled() -> bool:
    return os.environ.get('PY_M_MAP_NO_DOWNLOAD', '') not in ('', '0')


def missing_data_message(
    filename: str,
    what: str,
    download_hint: str,
    package_relative: tuple[str, ...] = (),
) -> str:
    """A message that names every location searched and how to fix it."""
    searched = '\n'.join(f'    {p}' for p in candidate_paths(filename, package_relative))
    return (
        f"{what} requires the data file '{filename}', which was not found.\n"
        f"  Searched:\n{searched}\n"
        f"  {download_hint}\n"
        f"  Then either place it in {USER_DATA_DIR}/ or set {ENV_VAR} to the "
        f"directory containing it."
    )
