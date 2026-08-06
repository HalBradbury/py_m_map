# py_m_map

A Python port of [m_map](https://www-old.eoas.ubc.ca/~rich/map.html), Rich
Pawlowicz's mapping toolbox for MATLAB, built on matplotlib, pyproj and shapely.

If you have MATLAB code or course material written against m_map, this is meant
to let you carry it across largely unchanged: the function names, the argument
conventions and the figure defaults deliberately mirror m_map.

```matlab
% MATLAB / m_map
m_proj('lambert', 'lon', [-160 -40], 'lat', [30 80]);
m_coast('patch', [1 .85 .7]);
m_elev('contourf');
m_grid('box', 'fancy');
```

```python
# Python / py_m_map
from py_m_map import m_proj, m_coast, m_elev, m_grid

m_proj('lambert', lon=[-160, -40], lat=[30, 80])
m_coast('patch', [1, 0.85, 0.7])
m_elev('contourf')
m_grid(box='fancy')
```

Why `m_`-prefixed names in Python? Because fidelity to m_map is the whole point
of the library — it is a deliberate choice, not an oversight. If you want an
idiomatic Python mapping API, use [cartopy](https://scitools.org.uk/cartopy)
directly; py_m_map is built on top of it.

## Install

```bash
pip install py_m_map
```

Requires Python 3.10 or newer. Dependencies: numpy, matplotlib, pyproj, shapely,
xarray, scipy and cartopy.

## Getting started

```python
import matplotlib.pyplot as plt
from py_m_map import m_proj, m_coast, m_grid, m_elev, m_contfbar

fig, ax = plt.subplots(figsize=(7, 6))

m_proj('lambert', lon=[-135, -120], lat=[47, 56])   # BC coast
m_elev('contourf', levels=range(-3000, 2001, 250))
m_coast('patch', [0.7, 0.7, 0.7])
m_grid(box='fancy')
m_contfbar([0.6, 0.95], 0.08, None, range(-3000, 2001, 250))

fig.savefig('bc_coast.png', dpi=200)
```

`m_proj` sets a module-level projection state that every other function reads, so
call it first — exactly as in MATLAB. Call `reset_state()` between figures.

## Data

**Topography works out of the box.** A 1° global grid is bundled with the
package, so `m_elev` needs no setup. It was produced by block-averaging ETOPO1
to one degree and agrees with m_map's own `m_topo.mat` to 8 m RMS.

**Coastlines download on first use.** `m_coast` and `m_landmask` use Natural
Earth via cartopy, and `m_gshhs*` uses GSHHS; both are fetched and cached by
cartopy automatically. The first call needs network access.

**High-resolution bathymetry is optional.** `m_etopo2` needs the full ETOPO1
1 arc-minute grid (~447 MB), which is far too large to ship. Download
`etopo1_ice_g_i2.bin` from
[NOAA NGDC](https://www.ngdc.noaa.gov/mgg/global/relief/ETOPO1/data/ice_surface/grid_registered/binary/)
and put it in `~/.py_m_map/`, or point `PY_M_MAP_DATA_DIR` at the directory
holding it. Without it, `m_etopo2` warns and falls back to the bundled 1° grid.

**The examples fetch their own data.** The satellite examples use real NOAA fields
(OI SST v2, NCEP reanalysis) downloaded on first run and cached alongside
everything else. All sources are open and unauthenticated. Any example whose data
cannot be reached skips with an explanatory message.

| Environment variable | Purpose |
|---|---|
| `PY_M_MAP_DATA_DIR` | Directory (or `os.pathsep`-separated list) searched for optional data files. |
| `PY_M_MAP_TOPO_FILE` | Override the bundled 1° grid with a 180×360 `.npz` or `.mat` — e.g. m_map's `m_topo.mat` for exact parity. |
| `PY_M_MAP_NO_DOWNLOAD` | Forbid all network fetches; missing data raises instead, naming every path searched. |
| `PY_M_MAP_FETCH_LARGE` | Allow the two 64 MB OISST example downloads (opt-in; they are skipped otherwise). |

## What is included

**Projections** — `m_proj` accepts, with prefix matching and m_map's aliases:
equidistant cylindrical, Mercator, Miller, Lambert conformal conic, Albers equal
area, stereographic, orthographic, azimuthal equal-area, UTM, oblique Mercator,
Mollweide, Hammer–Aitoff, Robinson and sinusoidal.

Not yet ported: azimuthal equidistant, gnomonic, satellite perspective,
transverse Mercator, Gall–Peters, cylindrical equal-area and Kavrayski VII.

**Functions**

| Area | Functions |
|---|---|
| Projection | `m_proj`, `m_ll2xy`, `m_xy2ll`, `get_state`, `reset_state` |
| Frame and grid | `m_grid` |
| Coastlines | `m_coast`, `m_landmask`, `m_gshhs`, `m_gshhs_c/l/i/h/f`, `m_usercoast` |
| Topography | `m_elev`, `m_etopo2`, `m_shadedrelief` |
| Fields | `m_contour`, `m_contourf`, `m_pcolor`, `m_image`, `m_hatch` |
| Colour | `m_colmap`, `m_contfbar` |
| Vectors | `m_quiver`, `m_vec`, `m_windbarb`, `m_windrose` |
| Geometry | `m_line`, `m_track`, `m_range_ring`, `m_text`, `m_title` |
| Decorations | `m_ruler`, `m_northarrow`, `m_utmgrid` |
| Geodesy | `m_lldist`, `m_idist`, `m_fdist`, `m_xydist` |

See [EXAMPLES.md](EXAMPLES.md) for a worked gallery with figures.

## Differences from m_map

- Coastline and bathymetry data come from Natural Earth, GSHHS and ETOPO1 rather
  than m_map's bundled databases, so coastlines will not be pixel-identical to
  MATLAB output.
- Options are Python keyword arguments (`m_grid(box='fancy')`) rather than
  MATLAB's positional name/value string pairs, though the names match.
- `xticklabels` / `yticklabels` control only whether labels are drawn; custom
  label text is not supported and warns if passed. `xlabeldir` is accepted but
  not implemented.
- Lakes and inland seas are handled correctly by `m_landmask` but are still drawn
  in the land colour by `m_coast`.
- Geomagnetic coordinates (`m_coord`, `m_geo2mag`, `m_mag2geo`) and interactive
  input (`m_ginput`) are not ported.

See `IMPLEMENTATION_PLAN.md` for the full status and `REVIEW.md` for known issues.

## Tests

```bash
pip install -e ".[test]"
pytest tests -q
```

The suite has two parts. `tests/test_regressions.py` makes numerical assertions
about coordinate transforms, land masking and colourbar behaviour. The
`test_example*.py` scripts render the gallery figures, and a `conftest.py` fixture
compares each rendered PNG against a stored reference in `tests/baseline/`.

Those references are specific to the rendering stack that produced them — a
different matplotlib or freetype will shift antialiasing and trip the comparison.
To skip it, or to bless an intended visual change:

```bash
PY_M_MAP_SKIP_BASELINE=1   pytest tests -q     # ignore the comparison
PY_M_MAP_UPDATE_BASELINE=1 pytest tests -q     # accept current output
```

On failure a three-panel baseline/current/difference image is written to
`tests/outputs/_baseline_diffs/`.

## Licence and credit

MIT — see [LICENSE](LICENSE).

py_m_map is an independent re-implementation; no m_map source or data is
included. The design, API and figure conventions are Rich Pawlowicz's, and m_map
deserves the credit in anything you publish using this. Bundled topography is
derived from ETOPO1 (Amante & Eakins, 2009, NOAA NGDC), a US Government work.
