# py_m_map — Implementation Plan

> Python port of Rich Pawlowicz's m_map MATLAB toolbox for oceanographic mapping.
> Reference MATLAB source: `../m_map/`

**Last reviewed: 2026-08-06.** This document is the design record: what was built,
how, and why. It is deliberately kept as the place where architectural decisions
live — the "Architectural Notes" section at the end has repeatedly turned out to be
the only written source for behaviour that is easy to get wrong, so check it before
changing rendering code.

Three companion documents carry things this one does not:

| Document | Holds |
|---|---|
| `REVIEW.md` | Code review findings (M1-M15), each with its failure case and how it was verified. The record of what was *wrong*. |
| `PUBLISHING.md` | Packaging and distribution readiness; what is still open before a release. |
| `CHANGELOG.md` | Release-facing summary, grouped by consequence. |

---

## Guiding Principles

- **Pythonic API**: keyword arguments throughout, no positional-string parameter chains.
- **Thin wrapper philosophy**: project coordinates with Pyproj; draw with vanilla Matplotlib.
- **API familiarity**: an m_map user should recognise every function name and parameter.
- **Correctness before completeness**: get one full example right before expanding.
- **No MATLAB quirks**: remove legacy MATLAB version checks; global-variable side-effects are contained in a clean state singleton.

---

## Package Structure

```
py_m_map/                    ← package root
├── py_m_map/
│   ├── __init__.py          # Public re-exports, __version__
│   ├── _state.py            # MapState singleton (replaces MAP_PROJECTION global)
│   ├── _data.py             # Optional-data location + fetch/cache (see below)
│   ├── data/
│   │   └── topo_1deg.npz    # Bundled 1° topography for m_elev (108 KB)
│   ├── projection.py        # m_proj, m_ll2xy, m_xy2ll
│   ├── grid.py              # m_grid
│   ├── colormaps.py         # m_colmap
│   ├── shaded_relief.py     # m_shadedrelief
│   ├── contour.py           # m_contourf, m_contour
│   ├── colorbar.py          # m_contfbar
│   ├── coast.py             # m_coast
│   ├── elevation.py         # m_elev
│   ├── etopo.py             # m_etopo2
│   ├── quiver.py            # m_quiver
│   ├── line.py              # m_line
│   ├── vec.py               # m_vec
│   ├── northarrow.py        # m_northarrow
│   ├── decorations.py       # m_ruler, m_utmgrid
│   ├── gshhs.py             # m_gshhs, m_gshhs_c/l/i/h/f
│   ├── range_ring.py        # m_range_ring
│   ├── hatch.py             # m_hatch
│   ├── text.py              # m_text, m_title
│   ├── geodesic.py          # m_lldist, m_idist, m_fdist, m_xydist
│   ├── pcolor.py            # m_pcolor
│   ├── image.py             # m_image
│   ├── usercoast.py         # m_usercoast
│   ├── windbarb.py          # m_windbarb
│   └── windrose.py          # m_windrose
│                            # (coordinates.py for m_coord/m_geo2mag was planned
│                            #  but never written — see Known Limitations)
├── tests/
│   ├── conftest.py          # Image-baseline comparison fixture (autouse)
│   ├── example_data.py      # Registry of the real NOAA datasets the examples fetch
│   ├── test_regressions.py  # 57 assertion-based tests, one per reviewed defect
│   ├── baseline/            # Committed reference PNGs; the comparison gate
│   │                        #   (excluded from the sdist — stack-specific)
│   ├── test_example1.py     ✓ complete
│   ├── test_example2.py     ✓ complete
│   ├── test_example3.py     ✓ complete
│   ├── test_example4.py     ✓ complete
│   ├── test_example5.py     ✓ complete
│   ├── test_example6.py     ✓ complete
│   ├── test_example7.py     ✓ complete
│   ├── test_example8.py     ✓ complete
│   ├── test_example9.py     ✓ complete
│   ├── test_example10.py    ✓ complete  (UTM ship track)
│   ├── test_sat_ex5.py      ✓ complete  (North Pacific winds + precipitation, Miller, m_windbarb)
│   ├── test_sat_ex8.py      ✓ complete  (satellite example 8)
│   ├── test_example11.py    ✓ complete
│   ├── test_example12.py    ✓ complete
│   ├── test_example13.py    ✓ complete
│   ├── test_example14.py    ✓ complete  (One Ocean LAEA: coast patch, m_elev contourf/image/shadedrelief)
│   ├── test_example15.py    ✓ complete  (Pacific-centred pcolor + stepped jet colourmap; Robinson projection)
│   ├── test_example15_inverse.py  ✓ complete  (land-masked pcolor, 3-panel, ruler box)
│   ├── test_example16.py    ✓ complete  (NE Pacific bathymetry, Mercator, m_etopo2 contourf)
│   ├── test_example17.py    ✓ complete  (South China Sea shaded relief, Mercator, m_etopo2 shadedrelief)
│   ├── test_example18.py    ✓ complete  (Vancouver Harbour UTM, m_shadedrelief, m_gshhs_f, NHN rivers, m_utmgrid, m_ruler, m_northarrow)
│   ├── test_example20.py    ✓ complete  (colourmap gallery)
│   ├── test_example19.py    ✓ complete  (wind roses)
│   ├── test_sat_ex1.py      ✓ real OISST v2 SST, Nov 1999 (fetched)
│   ├── test_sat_ex2.py      ✓ real OISST v2 sea-ice concentration, Sep 2012 (fetched)
│   ├── test_sat_ex4.py      ✓ real NE Pacific SST anomaly, "the Blob" (fetched)
│   ├── test_sat_ex6.py      ~ synthetic float tracks (real Argo index is 315 MB)
│   └── outputs/             # Freshly rendered figures; git-ignored
├── .github/workflows/       # tests matrix, image baseline (manual), packaging
├── README.md                # Front door
├── CHANGELOG.md             # Release-facing history
├── REVIEW.md                # Code review findings and their resolution
├── PUBLISHING.md            # Distribution readiness
├── IMPLEMENTATION_PLAN.md   # This file
├── EXAMPLES.md              # Gallery (20 basic + 6 satellite examples)
├── LICENSE                  # MIT, plus m_map/ETOPO1 acknowledgements
├── MANIFEST.in
└── pyproject.toml
```

`test_sat_ex3.py` (aerial photograph) and `test_sat_ex7.py` (ERS-1 SAR) were
**deleted**: neither source is publicly retrievable and the synthetic stand-ins —
three flat rectangles and a field of grey noise — demonstrated nothing.

### Optional data

Nothing outside the package is required any more. `m_elev` reads the bundled
`data/topo_1deg.npz`. Two things remain optional, and `_data.py` resolves both by
searching `$PY_M_MAP_DATA_DIR`, then `~/.py_m_map/`, then the legacy
package-relative paths, reporting every location searched when absent:

| File | Needed by | Size | Source |
|---|---|---|---|
| `etopo1_ice_g_i2.bin` | `m_etopo2` (falls back to `m_elev`) | ~447 MB | NGDC ETOPO1 ice-surface, grid-registered, little-endian int16 |
| `barkley_sound_1_navd88_2016.nc` | `sat_ex8` only (skips without it) | large | No stable open URL; must be supplied locally |

The example datasets (NOAA OI SST v2, NCEP reanalysis) are fetched on first use by
`_data.fetch_data_file` and cached in `~/.py_m_map/`; see `tests/example_data.py`.

---

## Dependencies

```toml
[project]
dependencies = [
    "numpy",
    "matplotlib>=3.5",  # >=3.5 for per-cell alpha arrays (m_pcolor clipping)
    "pyproj",           # Geodetic transforms and projections
    "shapely",          # Boundary clipping geometry
    "scipy",            # Interpolation, smoothing filters; .mat reading
    "cartopy",          # Natural Earth + GSHHS coastline data
]

[project.optional-dependencies]
test = ["pytest", "xarray", "netcdf4"]
```

Two corrections to what this section used to say:

- **`xarray` is not a runtime dependency.** Nothing in `py_m_map` imports it. It was
  listed for "loading netCDF elevation data", which `m_elev` never does — it reads
  the bundled `.npz` through numpy, and `m_etopo2` reads a raw binary. Only the
  example scripts read netCDF, so it belongs in the test extra.
- **`netcdf4` has to be declared alongside it.** xarray cannot open a netCDF file
  without a backend; a conda environment usually has one already, which is why the
  omission only surfaced on a clean CI runner.

`cartopy` is imported lazily inside functions, so `import py_m_map` works without
it; it is needed only when coastlines are drawn.

---

## Example-by-Example Progress

### `map.html#examples` (20 examples; cases 1–15 also in `m_demo.m`)

| Example | Description | Projection | Key Functions | Status |
|---------|-------------|------------|---------------|--------|
| **1** | Orthographic world map with coastline (Py_M_Map logo) | Orthographic | `m_coast` (patch), `m_grid` (linestyle='-'), `m_text` (Py_M_Map label with white bbox) | ✓ |
| **2** | Lambert conic — N. American topography | Lambert Conformal Conic | `m_coast` (patch), `m_elev` (contourf), `m_grid` (fancy) | ✓ |
| **3** | Polar stereographic — North Polar region | Stereographic | `m_elev` (contour), `m_coast` (patch), `m_grid` | ✓ |
| **4** | Interrupted sinusoidal + Mollweide world maps | Sinusoidal, Mollweide | `m_coast` (patch), `m_grid` (multi-segment) | ✓ |
| **5** | Oblique Mercator — NE Pacific quiver + contour | Oblique Mercator | `m_coast` (patch), `m_quiver`, `m_contour`, `m_grid` (oblique) | ✓ |
| **6** | Miller cylindrical — circular orbit track | Miller cylindrical | `m_coast` (line), `m_line`, `m_grid` (fancy) | ✓ |
| **7** | Lambert conic — Europe topography + colourbar | Lambert Conformal Conic | `m_etopo2`/`m_elev`, `m_contourf`, `m_contfbar`, `m_coast` | ✓ |
| **8** | Fancy vectors demonstration | Orthographic (zoomed) | `m_vec`, `m_coast`, `m_grid` | ✓ |
| **9** | GSHHS coastlines at multiple scales | Albers Equal-Area | `m_gshhs_c/l/i/h/f`, `m_coast`, `m_ruler` | ✓ |
| **10** | UTM grid with ship track | UTM | `m_gshhs_i`, `m_grid`, `m_ruler`, `m_track`, `m_northarrow` | ✓ |
| **11** | Hammer projection — Bangkok range rings | Hammer | `m_coast` (patch), `m_grid` (ellipse boundary, no gridlines), `m_line`, `m_range_ring` | ✓ |
| **12** | Lambert conic — BC coast with speckle and hatch | Lambert Conformal Conic | `m_gshhs_i` (line + speckle), `m_line`, `m_hatch` (single), `m_grid`, `m_text`, `m_northarrow` (type 3) | ✓ |
| **13** | Blue Ocean — great circle routes | Miller cylindrical | `m_coast`, `m_grid`, `m_lldist`, `m_line`, `m_text` | ✓ |
| **14** | One Ocean — multiple elevation display modes | Lambert Azimuthal Equal-Area | `m_elev` (contourf / image / shadedrelief), `m_coast`, `m_colmap`, `m_grid` | ✓ |
| **15** | Stepped jet colourmap with pcolor | Robinson (Pacific-centred) | `m_pcolor`, `m_coast`, `m_grid`, `m_colmap` | ✓ |
| **16** | NE Pacific bathymetry | Lambert Conformal Conic | `m_etopo2` (contourf), `m_gshhs_i`, `m_line`, `m_grid` (ruler box), `m_contfbar` (discrete/proportional), `m_colmap` (blues gamma-corrected) | ✓ |
| **17** | Shaded relief — South China Sea | Mercator | `m_etopo2` (shadedrelief), `m_gshhs_h`, `m_grid` (fancy), `m_contfbar` (continuous vertical), `m_colmap` (depth) | ✓ |
| **18** | Shaded relief — Vancouver Harbour with UTM grid | UTM | `m_shadedrelief`, DEM-derived Z=0 contour coastline, `m_grid`, `m_utmgrid`, `m_ruler` (4 km), `m_northarrow` | ✓ |
| **19** | Wind roses | Mercator | `m_usercoast`, `m_contourf`, `m_grid`, `m_northarrow`, `m_windrose`, `m_contfbar`, `m_colmap` | ✓ |
| **20** | Colourmap gallery | — | `m_colmap` (demonstration) | ✓ |

### Satellite examples (`map.html#satellite_examples`)

| Example | Description | Projection | Key Functions | Status |
|---------|-------------|------------|---------------|--------|
All surviving satellite examples now use **real, openly available NOAA data**,
fetched on first run and cached. The originals' HDF files are no longer publicly
retrievable, and the modern satellite archives that would replace them (NASA
OB.DAAC, NSIDC) require an Earthdata login, so NOAA PSL products were substituted
where an equivalent exists.

| Example | Description | Projection | Key Functions | Status |
|---------|-------------|------------|---------------|--------|
| **sat_ex1** | Global SST, Nov 1999 — the month the original mapped | Hammer-Aitoff | `m_pcolor`, `m_coast`, `m_grid` | ✓ real OISST v2 |
| **sat_ex2** | Arctic sea-ice concentration, Sep 2012 (record minimum) | Azimuthal Equal-Area | `m_pcolor`, `m_coast`, `m_grid` | ✓ real OISST v2 `icec` |
| **sat_ex3** | Aerial photo on UTM grid | UTM | — | ✗ **removed** — no open source; `m_image` on UTM is covered by example 18 |
| **sat_ex4** | NE Pacific SST anomaly, "the Blob" (repurposed from ocean colour) | Lambert Conformal Conic | `m_contourf`, `m_coast`, `m_grid`, `m_contfbar` | ✓ real OISST v2 anomaly |
| **sat_ex5** | Meteorological data — wind barbs | Miller cylindrical | `m_coast`, `m_contourf`, `m_windbarb`, `m_grid`, `m_contfbar`, `m_colmap` | ✓ real NCEP reanalysis |
| **sat_ex6** | ARGO drifter tracks | Lambert | `m_etopo2`, `m_gshhs_l`, `m_grid`, `m_vec`, `m_line`, `m_idist`, `m_fdist`, `m_contfbar` | ~ synthetic tracks (the Argo global index is 315 MB) |
| **sat_ex7** | SAR image of internal waves | Lambert | — | ✗ **removed** — no open source; ruler-box `m_pcolor` is covered by sat_ex5 |
| **sat_ex8** | Barkley Sound shaded relief + filled contours | Equidistant cylindrical | `m_shadedrelief`, `m_contourf`, `m_contfbar`, `m_colmap` | ✓ but **skips** without a local DEM |
| **sat_ex9** | Google Maps Static API overlay | Mercator | `m_image`, `m_grid`, `m_ruler` | ✗ skip — Google Static Maps API deprecated |

---

## Implemented Projections

| Projection | `m_proj` name(s) | Type | Notes |
|------------|-----------------|------|-------|
| Equidistant cylindrical | `'equidistant'`, `'eqc'` | rectangular | |
| Mercator | `'mercator'` | rectangular | |
| Miller cylindrical | `'miller'`, `'mil'` | rectangular | scalar `lat` → symmetric ±lat extent; `lon=None` → ±180° |
| Lambert Conformal Conic | `'lambert'` | conic | standard parallels auto from lat range |
| Sinusoidal | `'sinusoidal'` | pseudocylindrical | |
| Mollweide | `'mollweide'` | pseudocylindrical | |
| Oblique Mercator | `'oblique'` | oblique | two-point definition via `lat=[lat1,lat2]`, `lon=[lon1,lon2]` |
| Stereographic | `'stereographic'` | circular | `radius` param in degrees |
| Orthographic | `'orthographic'` | circular | `radius` param for zoomed views; back-hemisphere handled analytically |
| Albers Equal-Area Conic | `'albers'`, `'alb'`, `'aea'` | conic | standard parallels auto from lat range (mid ± span/6) |
| UTM | `'utm'` | rectangular | zone auto-computed from lon midpoint; `utm_zone` and `utm_south` stored in state |
| Hammer / Hammer-Aitoff | `'hammer'`, `'hammer-aitoff'` | pseudocylindrical | `lon=` sets centre longitude; `center_lon` stored in state for cut-meridian logic |
| Robinson | `'robinson'` | pseudocylindrical | `lon=` sets centre longitude; used in Example 15 (Pacific-centred world map) |
| Lambert Azimuthal Equal-Area | `'azimuthal equal-area'` | circular | `lon`/`lat` = centre point; `radius` in degrees; `center_lon`/`center_lat` stored in state |

## Not-Yet-Implemented Projections

m_map documentation lists 21 projections; the 7 not yet ported are:

| Projection | `m_proj` name(s) | Type | Notes |
|------------|-----------------|------|-------|
| Azimuthal Equidistant | `'azimuthal equidistant'` | circular | equidistant from centre point |
| Gnomonic | `'gnomonic'` | circular | perspective — great circles are straight lines |
| Satellite | `'satellite'` | circular | oblique perspective at specified orbital altitude |
| Transverse Mercator | `'transverse mercator'` | rectangular | conformal; distinct from UTM |
| Gall-Peters | `'gall-peters'` | rectangular | equal-area cylindrical |
| Cylindrical Equal-Area | `'cylindrical equal-area'` | rectangular | not recommended for most uses |
| Kavrayski VII | `'kavrayski'` | pseudocylindrical | added MATLAB v1.4o (Sept 2023) |

---

## Implemented Modules

### `_state.py`
`MapState` dataclass singleton. Fields: `projection_name`, `projection_type` (`'rectangular'`/`'oblique'`/`'conic'`/`'circular'`/`'pseudocylindrical'`), `lon_limits`, `lat_limits`, `proj` (pyproj.Proj), `x_limits`, `y_limits`, `center_lat`, `center_lon`. `center_lon` is set for all projections that have a meaningful centre longitude (Hammer, orthographic, etc.) and is used by `coast.py` and `grid.py` to determine the cut meridian.
- `title_y: Optional[float]` — axes-coordinate y position set by `m_grid` when `box='fancy'` so that `m_title()` places titles above the outer ruler border regardless of figure size; `None` when fancy box is not in use (falls back to `y=1.0`).

### `projection.py`
- `m_proj(name, *, lon, lat, radius, aspect, direction)` — all projections above
- `m_ll2xy(lon, lat, clip='on'|'off'|'patch')` — forward projection with optional clipping
- `m_xy2ll(x, y)` — inverse projection
- `lon=None` supported for Miller (defaults to ±180°)
- `radius` supported for orthographic/stereographic (zoomed circular views)

### `grid.py`
- `m_grid(**kwargs)` — dispatches to `_draw_grid_rectangular`, `_draw_grid_oblique`, `_draw_grid_conic`, or `_draw_grid_circular` based on `state.projection_type`
- **Fancy box** (`box='fancy'`, `boxstyle='fill'`): alternating black/white rectangles split at tick midpoints; global sequential counter ensures strict B/W/B/W alternation; `_draw_fancy_box` / `_draw_fancy_corner`
- **Ruler box** (`box='fancy'`, `boxstyle='line'`): same alternating patch layout as fancy box but black patches rendered as white fill + thin black centre line at bw/2 from the map edge; strip centre lines stop exactly at the map edge (x0/x1/y0/y1) and do not extend into corner squares; separator lines at every patch boundary; corner squares always white with (1) a diagonal from the inner corner to the outer corner and (2) up to two half-lines from the inner corner edges to the diagonal midpoint — the horizontal half-line is drawn when `c_h='k'` (adjacent horizontal-edge strip is black) and the vertical half-line when `c_v='k'` (adjacent vertical-edge strip is black), so a matched-colour corner shows an L-junction at the midpoint and a mismatched corner shows a single arm; **tick-at-corner case**: when a grid tick falls exactly on a corner coordinate (e.g. an x-tick at x0 or x1), `_draw_ruler_box` detects this via `np.isclose` and passes `tick_at_h=True` / `tick_at_v=True` to `_draw_ruler_corner`; the corner then draws a full-height separator line through the corner box at that position, and if the adjacent strip is white (`c_h != 'k'`) also draws the horizontal stub to the diagonal midpoint — if the adjacent strip is already black the existing centre line covers that path and no stub is added; `_draw_ruler_box` / `_draw_ruler_corner`; `boxstyle` is forwarded from the dispatcher to `_draw_grid_conic` so conic projections also support the ruler style — `_conic_fancy_edge` accepts a `style=` argument and renders curved ruler strips with separator lines + outer boundary; corners are white-filled parallelograms with outer V-shape boundary lines
- **Pixel-precise box rendering**: all Rectangle patches and `ax.fill()` polygon patches use `antialiased=False` (integer-pixel snap) to eliminate grey fringing at black/white edges; outer and inner border rectangles likewise; corner diagonal lines use `antialiased=True` + `solid_capstyle='butt'`; a `diag_offset_y` parameter (in display pixels, positive = up on screen, default 0) is available on both `_draw_ruler_corner` and `_draw_fancy_corner` via `ax.transData.transform` / `.inverted()` round-trip for fine sub-pixel alignment of the diagonal — currently unused (all corners at offset 0)
- **Outward tick suppression**: `tickdir='out'` tick marks are suppressed when `box='fancy'` (guarded by `box != 'fancy'`); the ruler strip already encodes tick positions through alternating black/white sections so outward marks at `clip_on=False` would bleed into the corner area
- **Title positioning**: after drawing the fancy box, `state.title_y = 1.0 + bw/(y1−y0) + 0.01` (axes coordinates) is stored so `m_title()` can place the title above the outer ruler border; any title already set on `ax` is repositioned immediately
- **Circular grid**: gridlines and labels drawn within the visible lat/lon region (not full -180–180 / -80–80); auto-ticks use `state.lat_limits`/`state.lon_limits` for zoomed views
- **Circular labels**: boundary-intersection approach — each gridline is sampled to find where it crosses the map circle boundary; label placed just outside at that angle. Works for both full-hemisphere and zoomed circular maps.
- **`_nice_ticks`**: selects from `[0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 20, 25, 30, 45, 60, 90]`
- **Conic outer mask**: a compound `PathPatch` (outer rectangle + reversed inner frame polygon, non-zero winding rule) at `zorder=9` masks the triangular corners between the curved Lambert conic frame and the rectangular axes extent; tick labels are drawn at `zorder=15` to render above the mask
- **Conic inward ticks**: `tickdir='in'` draws tick marks inward (in the `−outward_normal` direction) on all four frame edges, using the same boundary-normal arrays as the outward tick code
- Supported kwargs: `box`, `boxstyle`, `grid`/`linestyle`, `tickdir`, `fontsize`, `lon_ticks`, `lat_ticks`, `xticklabels`, `yticklabels`, `xtick`, `ytick`, `color`, `ticklen`, `yaxislocation`, `xaxislocation`, `xlabeldir`, `linewidth`
- **Full-world pseudocylindrical boundary**: for full-world Hammer/Mollweide (`lon_max − lon_min ≥ 359.9°`) the ellipse boundary is drawn using the cut meridian as both edges (cut±ε); partial-lobe sinusoidal/Mollweide projections use the standard lobe-boundary logic. The `full_world` guard prevents the cut-meridian boundary path from being applied to interrupted-projection lobes.
- **Pseudocylindrical parallel linspace bug fix**: parallels previously used `linspace(left_lon − 360, right_lon, n)` which, for Mollweide (clon=0), produced a 720°-wide range entirely outside lon_limits=[-180, 180] — `clip='on'` NaN'd ~half the points, leaving parallels short of the left edge. Fixed to `linspace(lon_min + ε, lon_max − ε, n)` which always spans the projection's actual coordinate range; applies to Robinson, Mollweide, Sinusoidal, Hammer, and all other pseudocylindrical types.

### `coast.py`
- `m_coast(mode, *, resolution, **kwargs)` — `mode` is `'line'`, `'patch'`, or `'fill'`
- `m_landmask(lon_grid, lat_grid, resolution='110m')` — returns boolean array (True = land) for any lon/lat grid; not exported in `__init__.py` (internal utility). Containment tested in geographic (lon, lat) space via `matplotlib.path.Path.contains_points`, avoiding NaN artefacts from projected-space polygon distortion. Cut meridian auto-detected from projection state: when the projection is full-world (`lon_max − lon_min ≥ 359.9°`) and `lon_max` is not near ±180°, `cut = lon_max` (e.g. lon_max=30 for Pacific-centred Robinson); otherwise `cut=None` and standard ±180° bounding box is used. Land polygons east of the cut are shifted −360° so coordinates are continuous with the grid's remapped range.
- **Auto-resolution**: selects Natural Earth resolution based on map span: `'10m'` (< 30°), `'50m'` (< 90°), `'110m'` (global). Override with `resolution=` keyword.
- **Rectangular projections**: antimeridian NaN break (detects x-jumps > 50% of map width, inserts NaN)
- **Circular projections**: back-hemisphere vertices pushed radially to 3R using analytic orthographic direction formula; Shapely disk clip applied. Large land polygons (e.g. Africa+Eurasia combined) can project such that their 2-D interior encloses the map-centre ocean rather than the land — detected by comparing `poly.contains(center_geo)` against `clipped.contains(origin)`; if they disagree the intersection is replaced by `horizon_disk.difference(proj_poly)`.
- **Full-world pseudocylindrical patch**: each land polygon ring is split at the cut meridian via `_split_ring_at_cut` before projecting. Boundary vertices are offset ±0.01° from the exact cut so each sub-ring projects to its own edge of the map (see Architectural Notes). No Shapely clipping needed; latitude AABB rejection still applied.

### `elevation.py`
- `m_elev(mode, levels, upsample, **kwargs)` — modes: `'contourf'`, `'contour'`, `'shadedrelief'`, `'image'`; optional bicubic upsampling via `scipy.interpolate.RectBivariateSpline`
- **Topography source changed.** It used to load `m_topo.mat` from `../m_map/private/`, i.e. from a MATLAB m_map installation beside the source tree — so it was dead for anyone who installed the wheel. It now reads `data/topo_1deg.npz`, bundled in the package (108 KB), produced by block-averaging ETOPO1 to 1°. Cross-checked against `m_topo.mat`: mean difference +0.3 m, RMS 8.0 m, correlation 1.00000, land/ocean sign agreement 99.95 % — interchangeable in practice.
- The bundled grid is preferred **even when `m_topo.mat` is present**, so the same code gives the same figure on every machine. `PY_M_MAP_TOPO_FILE` overrides it with a 180×360 `.npz` or `.mat` for exact MATLAB parity.
- **Longitude wrap-around padding**: for full-global coverage (radius ≥ 359°), `_extract_topo` pads one wrap-around column at each end (`lons[-1]+1` → copy of first column; `lons[0]-1` → copy of last column) so that `RegularGridInterpolator` queries near ±180° never return NaN.

### `etopo.py`
- `m_etopo2(mode, levels, **kwargs)` — reads `etopo1_ice_g_i2.bin` (1 arc-minute, little-endian int16), located via `_data.py` rather than a fixed relative path
- Constants: `_NX=21600`, `_NY=10800`, `_PTSPERLINE=21601` (grid-referenced), `_DECMAX=800`
- Row-by-row binary read with seek; decimation to ≤800 pts/axis; sorted column output (fixes prime-meridian wrap)
- Falls back to `m_elev` with a warning naming every path searched when the binary is absent
- **Antimeridian straddle**: the two-piece read is selected by testing the column indices *before* the modulo wrap. Testing afterwards can never fire (a modulo result is always in `[0, _NX)`), which left the straddle branch as dead code and handed the contiguous branch a negative array width — see REVIEW.md H2.

### `shaded_relief.py`
- `m_shadedrelief(lon, lat, Z, **kwargs)` — lighting via complex gradient rotation; tanh saturation; true-colour RGB image via `imshow`
- **Inverse reprojection for circular/pseudo projections**: for projections where geographic lon/lat do not map uniformly onto projected x/y (LAEA, orthographic, Mollweide, …), builds a regular grid in projected space, inverse-projects via `m_xy2ll`, interpolates Z with `RegularGridInterpolator`, then computes gradients with uniform dx/dy spacing. Avoids the severe spacing distortion that occurs when using forward projection at a fixed mean lat/lon.
- **Colormap resolution**: `_resolve_cmap` reads the most recent image or collection from the current axes if no colormap is given; falls back to viridis.
- **z-order**: `_draw_grid_circular` white circle background rendered at `zorder=-1` so `imshow` (default zorder=0) sits above it.

### `contour.py`
- `m_contourf(lon, lat, data, levels, *, edgecolor, **kwargs)` — `edgecolor='none'` suppresses overlay contour lines
- `m_contour(lon, lat, data, levels, **kwargs)`

### `colorbar.py`
- `m_contfbar(xpos, ypos, data, levels, *, axfrac, endpiece, extend, levels_mode, edgecolor, fontsize, **kwargs)`
- **Discrete rendering** (`render_continuous=False`): uses `BoundaryNorm(clevel, ncolors=n_bands)` + `spacing='proportional'` so band widths are linear in data space regardless of unequal interval sizes; `drawedges=True` draws black divider lines between bands; ceiling division `-(-n // 6)` used for tick stride to handle cases where `len(clevel)` is just above the reduction threshold
- **Continuous rendering** (`render_continuous=True`): triggered when colormap has > 50 colours or > 50 levels; uses `ScalarMappable` with `Normalize`; tick density also reduced with ceiling division
- **`extend` parameter**: when supplied explicitly (`'both'`, `'min'`, `'max'`, `'neither'`) it is honoured directly; otherwise `endpiece=True` auto-detects which caps are needed from the data range
- Colorbar title bold weight set via `set_title(..., fontweight='bold')` in the test files

### `colormaps.py`
- `m_colmap(name, n)` — embedded RGB lookup tables; falls back to matplotlib colormaps for unknown names

### `quiver.py`
- `m_quiver(lon, lat, u, v, **kwargs)`

### `line.py`
- `m_line(lon, lat, **kwargs)` — geographic line/point plotting; antimeridian NaN break via `m_ll2xy(clip='off')` + finite-value masking

### `gshhs.py`
- `m_gshhs(scale, style, *args, **kwargs)` — draw GSHHS coastlines; scale `'c'/'l'/'i'/'h'/'f'`; style `'patch'`, `'line'`, or `'speckle'`
- `m_gshhs_c/l/i/h/f(style, *args, **kwargs)` — convenience wrappers for each resolution
- **Hierarchical patch rendering**: levels 1 (land) and 3 (islands-in-lakes) filled with land colour; levels 2 (lakes) and 4 (ponds) filled with axes background to cut out water; missing levels silently skipped
- **Speckle style**: iterates level-1 land polygons within the map bounds; calls `_hatch_xy` with style `'speckle'`, width 5 pts, step 2 pts to scatter dot markers along each coastline boundary on the land side
- Data loaded via `cartopy.io.shapereader.gshhs(scale, level)`; emits `UserWarning` (naming the failed scale/level and suggesting a pre-download command) then returns `[]` on any exception — previously silent
- Dispatches to `_draw_geoms_geographic_clip` (rectangular/conic), `_draw_geoms_oblique`, or `_draw_geoms_circular` — same clip strategies as `coast.py`

### `range_ring.py`
- `m_range_ring(lon0, lat0, ranges, *, npts=360, **kwargs)` — draws great-circle range rings centred on `(lon0, lat0)`
- `ranges`: array of ring radii in kilometres
- Uses `pyproj.Geod(a=6378137, f=0)` (spherical Earth) for forward geodesic; 360 azimuths per ring
- NaN breaks inserted at projected x-jumps > 50% of map width to handle antimeridian / projection discontinuities

### `track.py`
- `m_track(lon, lat, navtimes, *, ticks, times, dates, timefmt, datefmt, color, orient, clip, **kwargs)` — ship trackline with perpendicular tick marks and time/date labels
- `navtimes` accepts list of `datetime` objects; converted to relative minutes from first point
- `ticks=0` places a tick at every position; `ticks>0` interpolates to whole-minute multiples
- `orient='upright'` flips labels 180° when angle would make them upside-down
- Track and annotations drawn at zorder 11–13 (above fancy box at zorder 10)

### `decorations.py`
- `m_ruler(xpos, ypos, *, nbar, units, **kwargs)` — geographic scale bar
- `m_utmgrid(*, box, tickdir, fontsize, linestyle, linewidth, grid, xaxislocation, yaxislocation, **kwargs)` — UTM-coordinate grid with meter labels; auto-selects tick step targeting 4–8 ticks per axis
- `xpos=[x0, x1]` and `ypos` are fractions of map extent [0, 1]
- Geodesic distance computed via `pyproj.Geod(ellps='sphere')` from inverse projection of bar endpoints
- Distance snapped to a nice round value from `_NICE_KM = [0.1, 0.2, 0.5, 1, 2, 4, 5, 10, …]`; bar width scaled proportionally; 4 km added to table so example 18 snaps cleanly
- Solid black filled rectangle + tick marks at each of `nbar` divisions + labels at left (0), mid (nice/2), right (nice units)

### `vec.py`
- `m_vec(scale, lon, lat, u, v, color, *, headangle, headlength, headwidth, headstyle, shaftwidth, centered, key, edgeclip, curvature, **patch_kwargs)`
- Arrow polygon built in local frame (+x = arrow direction), rotated via complex multiplication, translated to projected tail position
- **`edgeclip`**: uses `shapely.geometry.Polygon.intersection(disk)` for circular maps; rectangular maps use reprojection clipping
- Curved arrows: circular arc shaft with radius `rad = L/(|curvature|·π/180)`
- Colour-mapped arrows via per-arrow RGB from current colormap; key arrow forced horizontal with text label

---

### `northarrow.py`
- `m_northarrow(lon, lat, scale, *, type, aspect, linewi, **kwargs)` — north arrow / compass rose at geographic position
- Types 1–4: simple arrow, half-arrow, 4-point rose, 8-point rose (default)
- **North direction**: computed by projecting `(lon, lat)` and `(lon, lat+0.01)`, forming a complex unit vector `dN` pointing north in map coordinates; all template shapes are scaled/rotated by `dN * scale`
- **"N" label**: rendered as `ax.text()` sized proportionally via `ax.transData.transform()` (a self-intersecting 7-point polygon path was replaced because matplotlib's fill rule caused a wide horizontal band artefact); fontsize scaled to 1.5× the projected half-height of the label zone
- **zorder**: defaults to `zorder=11` (above the frame box at 10); `zorder` from `**kwargs` is forwarded to both the Polygon patches and the "N" text so they stay co-planar

### `hatch.py`
- `m_hatch(lon, lat, style, angle, step, **kwargs)` — hatch or speckle inside a geographic polygon
- `style`: `'single'` — parallel lines at `angle` degrees; `'cross'` — lines at `angle` and `angle+90`; `'speckle'` — dot markers within `angle` pts of boundary (inward); `'outspeckle'` — outward
- `step` — spacing between hatch lines or dots in typography points
- **Point-space scaling**: `_get_pts_per_data` uses `state.x_limits`/`y_limits` (not `ax.get_xlim()`) because clip='off' projections can inflate the matplotlib auto-scale to far-out-of-bounds extents
- **Speckle dot clipping**: after computing dot positions, dots outside `state.x_limits`/`y_limits` are removed to prevent speckle appearing in areas outside the map frame
- **GSHHS polygon winding**: GSHHS level-1 land polygons from cartopy are clockwise (CW) in projected coordinates; the left-hand normal `(-dy/l, dx/l)` therefore points outward (ocean), so `sign=-1` for `outward=False` correctly places speckle inward (land side)
- `_hatch_xy(ax, x, y, style, angle, step, **kwargs)` — same algorithm operating on already-projected map coords; used internally by `gshhs.py`

### `windbarb.py`
- `m_windbarb(lon, lat, u, v, scale=0.9, *, units='knots', **kwargs)` — MATLAB-faithful meteorological wind barbs on the current map projection
- Barbs drawn as NaN-separated line segments via `ax.plot`; no use of `ax.barbs`
- 18 segment templates in `_SEGS` (full barbs 1–8, half barbs, pennant slants, base shaft); 18 speed-threshold boolean masks in `_masks(umag)` covering 2.5–127.5+ kt
- Wind direction rotated from geographic to map coordinates using finite-difference north (`lat+0.001`) and east (`lon+0.001/cos_lat`) unit vectors
- `scale2 = scale × (x_range / n_cols)` mirrors MATLAB's barb-length scaling formula
- `units` kwarg converts m/s, km/h, mph to knots for barb-count symbology; all drawing kwargs forwarded to `ax.plot`

### `usercoast.py`
- `m_usercoast(source, style, *args, **kwargs)` — draw a user-supplied coastline; `source` accepts a MATLAB `.mat` file, a shapefile/GeoJSON path, or a raw Nx2 NaN-separated array
- Styles: `'line'`, `'patch'`/`'fill'`, `'speckle'`
- Geographic clip (rectangular/conic/pseudo) vs projected clip (circular/oblique) dispatched by `state.projection_type`; same densification + Shapely intersection strategy as `coast.py`
- `_load_shapefile` handles `Polygon`/`MultiPolygon` (filled with signed area) and `LineString`/`MultiLineString` (area set to 1.0); unsupported geometry types are silently skipped

### `text.py`
- `m_text(lon, lat, s, **kwargs)` — projects `(lon, lat)` via `m_ll2xy(clip='off')` and calls `ax.text()`; list/tuple `s` joined with newlines; default alignment `ha='center'`, `va='center'`
- `m_title(text, ax=None, **kwargs)` — wrapper around `ax.set_title()` that reads `state.title_y` (set by `m_grid` after a fancy box) and passes it as the default `y` parameter; falls back to `y=1.0` when no fancy box has been drawn; use in place of `ax.set_title()` whenever `box='fancy'` is active to ensure the title clears the outer ruler border at any figure size

### `pcolor.py`
- `m_pcolor(lon, lat, data, **kwargs)` — projects a geographically gridded lon/lat array, then calls `ax.pcolormesh`. Handles antimeridian jumps (|Δx| > 50 % map width). Supports `shading` kwarg; default is `'auto'`, which treats same-shaped coordinates as cell **centres**.
- **Off-map cells are drawn transparent, via a per-cell `alpha` array** — not merely set to NaN. NaN routes them through the colormap's "bad" colour, which is the same channel the caller's own missing data uses: with an opaque `set_bad` every off-map cell is painted too, and a call whose data lies entirely off the map covers the whole figure. Note that masking the *coordinates* instead is not an option — matplotlib rejects non-finite or masked coordinates in `pcolormesh` outright. No alpha array is attached when nothing is clipped, so unaffected figures are untouched. See REVIEW.md M9.

### `image.py`
- `m_image(lon, lat, img, **kwargs)` — places an RGB or RGBA raster image on the map using `ax.imshow` with the correct `extent` in projected coordinates. For cylindrical projections the extent is computed directly from projected corners; for other projections a grid-warp approach is used.

### `geodesic.py`
- `m_lldist(lon, lat, N)` — Haversine great-circle distances (km) between successive waypoints; optional N-point geodesics via Cartesian unit-vector SLERP returning `(dist, lons, lats)` arrays of shape `(n−1, N+1)`
- `m_idist(lon1, lat1, lon2, lat2, spheroid)` — inverse geodesic via `pyproj.Geod`; returns `(dist_m, az12, az21)`
- `m_fdist(lon1, lat1, a12, s, spheroid)` — forward geodesic via `pyproj.Geod`; returns `(lon2, lat2, az21)`
- `m_xydist(x, y)` — inverse-projects map coords to lon/lat then calls `m_lldist`

## Known Limitations / Not Yet Implemented

### Missing projection support (7 of 21 unported)

Azimuthal Equidistant, Gnomonic, Satellite (perspective), Transverse Mercator, Gall-Peters, Cylindrical Equal-Area, Kavrayski VII. All common projections are covered; missing ones are niche. See the Not-Yet-Implemented Projections table above.

### `m_etopo2` missing render modes

MATLAB `m_etopo2` supports five modes: `'contourf'`, `'contour'`, `'pcolor'`, `'image'`, `'shadedrelief'`. Python `etopo.py` implements `'contourf'`, `'contour'`, and `'shadedrelief'` only. The `'pcolor'` and `'image'` modes are not yet implemented; `m_elev` covers both as a fallback.

### Test coverage — two layers, and what neither covers

`tests/test_regressions.py` holds 57 assertion-based tests, one per defect found in
the code review: projection round-trips, state leakage between `m_proj` calls, land
masking with polygon holes, ETOPO1 antimeridian reads, colourbar discrete/continuous
selection, `m_pcolor` clipping, and the tick-label placement rules for circular,
pseudocylindrical and ruler-box frames.

`tests/conftest.py` adds an image baseline: every PNG an example writes is compared
against `tests/baseline/` at **zero** pixel tolerance, with a
baseline/current/difference panel written on failure. Regenerate with
`PY_M_MAP_UPDATE_BASELINE=1 pytest tests -q`; skip with `PY_M_MAP_SKIP_BASELINE=1`.

That guard has earned its place — it caught five regressions introduced *while*
fixing the reviewed defects, every one of which the assertion tests passed.

What is still not covered:

- The 27 example scripts themselves assert nothing beyond "savefig did not raise";
  the baseline comparison is what makes them meaningful, and it is stack-specific.
- Individual functions in `colormaps.py`, `hatch.py`, `windrose.py`, `windbarb.py`
  and `decorations.py` have no unit tests. **Vector rotation in particular**
  (`m_quiver`, `m_vec`, `m_windbarb`) has no numerical test that a northward vector
  plots as north on a conic or stereographic projection — a plausible-looking wrong
  answer would pass.
- The baseline cannot run in CI while the GSHHS download URL returns 404: a clean
  runner omits those coastlines, so the comparison would fail on data availability.
  It is a local pre-release gate.

### Lakes are masked but not rendered

`m_landmask` handles polygon interior rings correctly, so enclosed water (the
Caspian, lakes) is no longer reported as land. `m_coast` still *fills* them with the
land colour. Fixing the drawing needs a shared compound-`PathPatch` helper adopted
by all four `_draw_patch*` functions, with interior rings carried through
`_split_ring_at_cut` — the antimeridian cases are the hard part. Numerical results
are correct; this is cosmetic. (REVIEW.md M4.)

### Parameters accepted but not implemented

`xticklabels` / `yticklabels` honour only whether labels are drawn — custom label
*text* is discarded. `xlabeldir` is accepted and never read. Both now emit a
`UserWarning` rather than failing silently, and the docstrings say so. Implementing
them means threading a label sequence through all five projection renderers, and for
circular frames "tick order" is not well defined where labels sit at boundary
intersections.

### Not typed

No public function has a fully annotated signature (12 of 41 have no parameter
annotations at all; 20 declare a return type). No `py.typed` marker is shipped —
adding one would promise typing the package does not have. Annotate the public API
first.

### GSHHS data source is broken upstream

The URL `m_gshhs` uses via cartopy returns 404, so coastlines are silently omitted
with a warning on any machine without a cached copy. This affects examples 9, 10, 12,
16, 17, 18 and sat_ex6, and is why the image baseline cannot run in CI.

### Geomagnetic coordinate support absent

`m_coord`, `m_geo2mag`, `m_mag2geo` are not implemented. These depend on IGRF coefficient files and are a specialist requirement; they are listed under "Probably not worth porting."

### No interactive input

`m_ginput` (interactive mouse clicks to geographic coordinates) is not implemented and is not planned. Users should use matplotlib event callbacks directly.

### `m_windrose` synthetic data only

`m_windrose` is implemented (`windrose.py`); example 19 runs against synthetic wind records. The MATLAB reference uses real station data from the Strait of Georgia, which is not publicly available in the m_map package.

### Confidence levels on edge cases

- **Medium confidence**: circular-projection clipping (tested on orthographic/stereographic; less coverage on LAEA), pseudocylindrical cut-meridian logic (tested on Hammer, Robinson; interrupted-lobe sinusoidal less tested), antimeridian handling at exact ±180°.
- **Lower confidence**: zoomed circular views with `radius` parameter across all projection types, Oblique Mercator near the poles, Miller cylindrical at high latitudes.

---

## Next Steps

Priority is roughly: unlock the most remaining examples with the fewest new modules, working from low complexity to high.

### ~~Phase 5 — Geodesic functions (`geodesic.py`)~~ ✓ Complete

Unlocks example 13 and sat_ex6.

| Function | MATLAB source | Notes |
|----------|--------------|-------|
| `m_lldist` | `m_lldist.m` | great-circle distance and N-point geodesics between waypoints; spherical Haversine |
| `m_idist` | `m_idist.m` | inverse geodesic: distance and azimuths between two points (pyproj.Geod) |
| `m_fdist` | `m_fdist.m` | forward geodesic: endpoint given start + azimuth + distance (pyproj.Geod) |
| `m_xydist` | `m_xydist.m` | great-circle distances from map coordinates via inverse projection + `m_lldist` |

> The phase list below is kept as history. Some entries refer to satellite examples
> that were later removed (sat_ex3, sat_ex7) — see the satellite examples table.

### ~~Phase 6 — `m_pcolor` (`pcolor.py`)~~ ✓ Complete

Unlocked examples 15, sat_ex1, sat_ex4 (and sat_ex7, since removed).

### ~~Phase 7 — `m_image` (`image.py`)~~ ✓ Complete

Unlocked sat_ex2 and sat_ex9 (partial), plus sat_ex3, since removed. Note sat_ex2
now uses `m_pcolor` on a geographic grid rather than `m_image` on EASE-Grid
coordinates.

### ~~Phase 8 — Elevation image mode (`elevation.py`)~~ ✓ Complete

Unlocks example 14.  Added `'image'` mode to `m_elev`; delegates to `m_image`.  Also fixed ±180° interpolation gap in `_extract_topo` via wrap-around padding.

### ~~Phase 9 — `m_usercoast` (`usercoast.py`)~~ ✓ Complete

Unlocks example 19 (example 18 uses `m_gshhs_f` instead).  Loads a user-supplied coastline from a MATLAB `.mat` file (`ncst`/`Area` arrays), a shapefile, or a raw Nx2 array; draws using the same patch/line/speckle strategies as `coast.py`.  `.mat` loader uses `scipy.io.loadmat`; shapefile path uses `cartopy.io.shapereader`.

### ~~Phase 10 — `m_windbarb` (`windbarb.py`)~~ ✓ Complete

Unlocks sat_ex5.  Wind barbs drawn as NaN-separated line segments in projected data coordinates (MATLAB-faithful; no `ax.barbs`).  18 segment types (`_SEGS`) and 18 speed-threshold masks (`_masks`) covering full barbs, half barbs, and pennants from 2.5 kt to >127.5 kt.  `scale2 = scale × x_range / n_cols` mirrors MATLAB's barb-length formula.  Local wind direction rotated from geographic to map coordinates via finite-difference north/east unit vectors.

### ~~Phase 11 — `m_windrose` (`windrose.py`)~~ ✓ Complete

Unlocks example 19.  Fan-shaped patches drawn in projected map space; bar angular width proportional to radius.  `nspeeds` defines speed-bin edges; `ndirs` sets directional resolution; `size` controls rose radius as a fraction of map width.  Returns a list of `PatchCollection` objects (one per station) for post-hoc colormap/clim assignment.

### ~~Phase 12 — Remaining `m_etopo2` modes~~ ✓ Complete

Examples 16–17 complete.  `m_etopo2` supports `'contourf'`, `'contour'`, and `'shadedrelief'` modes; ruler-style fancy box works for conic projections; discrete proportional colorbar with black dividers implemented.  MATLAB also has `'pcolor'` and `'image'` modes not yet ported (low priority — `m_elev` covers both as a fallback).

### Phase 13 — Minor geometry functions

Low priority; needed for completeness.  Functions marked **trivial** are thin wrappers (< 20 lines); **medium** require non-trivial coordinate handling.

| Function | Effort | Notes |
|----------|--------|-------|
| `m_patch` | Trivial | Geographic polygon patch — `m_line` + `ax.fill`; add to `line.py` |
| `m_scatter` | Trivial | `ax.scatter` after `m_ll2xy`; add to `line.py` |
| `m_arrow` | Trivial | Simple single arrows (distinct from `m_vec` fancy arrows) |
| `m_legend` | Trivial | Thin wrapper around `ax.legend` placed in map coordinates |
| `m_rectangle` | Low | Axis-aligned rectangles in geographic coordinates |
| `m_streamline` | Low | `ax.streamplot` after projecting the velocity grid |
| `m_annotation` | Low | Text annotation with leader line |
| `m_ellipse` | Medium | Tidal ellipses at map positions — requires rotation to local north |
| `m_scale` | — | Likely duplicate of `m_ruler`; verify against MATLAB before porting |

### ~~Phase 14 — Satellite example tests~~ ✓ Complete

Rebuilt on real, openly available NOAA data rather than synthetic stand-ins; see the
satellite examples table above. `sat_ex3` and `sat_ex7` were removed, `sat_ex4` was
repurposed to an SST anomaly (no open ocean-colour product exists), and `sat_ex6`
keeps synthetic float tracks because the Argo global index is 315 MB.

### ~~Phase 15 — Unit test suite~~ ✓ Largely complete

`tests/test_regressions.py` (57 tests) plus the image baseline in `conftest.py`.
Progress against the original targets:

| Target | Status |
|--------|--------|
| `projection.py` | ✓ round-trips for lambert/albers/oblique, scalar and array input, clip paths, state-leak guards |
| `geodesic.py` | ~ exercised indirectly (`m_lldist` checked against 111.32·cos φ); no dedicated table of known geodetic values |
| `coast.py` | ✓ polygon holes (`m_landmask`); antimeridian and back-hemisphere logic still untested directly |
| `grid.py` | ✓ label placement for circular / pseudocylindrical / ruler-box corners; `_nice_ticks` output still untested |
| `colormaps.py` | ✗ not started |
| `hatch.py` | ✗ not started |

Highest-value remaining gap is **vector rotation** — see Known Limitations.

### Probably not worth porting

| Function | Reason |
|----------|--------|
| `m_ginput` | Interactive mouse input — not useful outside MATLAB figures |
| `m_shaperead` | Python has `geopandas`/`cartopy` shapefile readers |
| `m_plotbndry` | Reads Canada-specific boundary `.mat` files; use `m_usercoast` instead |
| `m_tbase` / `m_tba2b` | Depend on private binary terrain data files specific to the MATLAB package |
| `m_ungrid` | Nearest-neighbour interpolation onto a regular grid — covered by `scipy.interpolate` |
| `m_coord` / `m_geo2mag` / `m_mag2geo` | Geomagnetic coordinate conversions; highly specialised, depend on IGRF coefficient files |
| sat_ex9 (Google Maps) | Google Static Maps API is deprecated / requires paid key |

---

## Architectural Notes

### Data Orientation Convention

| Context | Array shape | Notes |
|---------|-------------|-------|
| MATLAB `ncread` Band1 | (lon, lat) | MATLAB column-major; ncread gives (nlon, nlat) |
| Python xarray Band1 | (lat, lon) | CF convention |
| `m_shadedrelief(lon, lat, Z)` | Z: (nlat, nlon) | Rows = latitude (y) |
| `m_contourf(lon, lat, data)` | data: (nlat, nlon) | Same |

In MATLAB Example 8, `Z'` transposes (nlon, nlat) → (nlat, nlon). In Python, xarray already gives (nlat, nlon) — no transpose needed.

### Fancy Box

Each tick interval is split at its midpoint into two sub-segments. A global sequential counter (not per-interval `i % 2`) assigns colours, giving strict B/W/B/W alternation with no same-colour adjacency at interval boundaries.

### Antimeridian Wrapping (cylindrical projections)

Coastline segments crossing the antimeridian cause a jump in projected x of ≈ full map width. Detected as `|Δx| > 0.5 * x_range`; a NaN is inserted to break the plotted line.

### Orthographic Back-Hemisphere Clipping

pyproj returns `inf` for points on the back hemisphere. Rather than mapping all such points to the same proxy coordinate (which creates a spurious chord), each back-hemisphere point's angular direction is computed analytically:

```python
xb = cos(lat) * sin(lon - lon0)
yb = sin(lat)*cos(lat0) - cos(lat)*sin(lat0)*cos(lon - lon0)
```

The point is then pushed to `safe = 3R` in direction `(xb, yb)/||(xb, yb)||`. Shapely disk intersection then clips correctly.

### Gradient Direction Convention

NumPy `np.gradient(Z, y, x)` returns `[dZ/dy, dZ/dx]`. MATLAB `gradient(Z, x, y)` returns `[dZ/dx, dZ/dy]`. Therefore:

```matlab
[Fx, Fy] = gradient(Z, x*R, y*R)
```
→
```python
dZdy, dZdx = np.gradient(Z, y * R, x * R)
```

### Pseudocylindrical Cut-Meridian Ring Splitting

For full-world Hammer (and similar) projections centred at `lon_0`, the "cut meridian" is at `cut = lon_0 − 180°`. Any land polygon with vertices on both sides of `cut` would, if projected naïvely, have its x-coordinates jump from near `+x_max` to near `−x_max` within a single polygon — causing `ax.fill()` to draw a horizontal band across the entire map.

`_split_ring_at_cut(lon, lat, cut_lon)` resolves this:
1. Normalise all ring longitudes to `[0, 360)` relative to `cut_lon`. Values in `(0, 180)` map to the left half of the projection (x < 0); values in `(180, 360)` to the right half (x > 0).
2. Compute circular diffs. Edges where `|diff| > 180°` cross the cut.
3. At each crossing, interpolate `lat` at the exact cut and split the ring into sub-rings, placing the boundary vertex at `cut_at = ε` or `360 − ε` depending on which side the current sub-ring is on.
4. The ±ε offset (0.01°) is essential: the Hammer projection formula evaluates `lon = cut_lon` to only one edge (the left edge, x = −x_max). Without the offset both sub-ring boundary vertices project to the same x value; with it they project to opposite edges.
5. The final remnant of the walk is merged with the first sub-ring (closed-ring invariant: the ring starts and ends on the same side of the cut for a valid polygon).

### zorder Convention

Library functions pin map-frame elements to explicit zorders so they always sit above data regardless of draw order. Data layers (imshow, contourf, plot) use matplotlib defaults and rely on draw order for their relative stacking. The convention is:

| Layer | zorder | Examples |
|-------|--------|---------|
| Background fill | 0 | `ax.fill` in `_draw_grid_*` |
| Grid lines | 2 | `grid.py` line plots |
| Map frame / box | 10 | `_draw_fancy_box`, `_draw_ruler_box` |
| Tick marks | 12 | frame tick lines |
| Decorations (ruler, north arrow) | 11 | `m_ruler`, `m_northarrow` (default) |
| Tick labels | 15 | `ax.text` in `grid.py` |

Caller code should not need to pass explicit `zorder` for standard usage; any layer that must always sit above the frame should set its own default in the library function.

### Tick Label Placement on Non-Rectangular Frames

This was the weakest area of the codebase; six separate defects (REVIEW.md M10-M15)
all traced to one mistake, worth stating plainly because it is easy to repeat:

> **Labels were positioned at an extremum of the projected boundary** —
> bottom-most for a meridian, left-most for a parallel — **which is only well
> defined when that boundary is a rectangle.** On a circle the extremum is a single
> point many gridlines share; on a pseudocylindrical outline it is a pole where
> every meridian converges.

**Circular maps** (orthographic, stereographic, azimuthal). Labels go where
gridlines cross the boundary circle: for each meridian the bottom-most inside point,
for each parallel the left-most. Then:

- Placement is **radial, and the text is horizontal** — not tangential. A tangent is
  forced to exactly ±90° at the left and right extremes, and normalising into
  (−90°, 90°] cannot reconcile them: one side reads bottom-to-top and the other
  top-to-bottom, so one looks inverted. No rotation rule is both continuous around
  the circle and never upside-down. Clearance from the boundary comes from anchoring
  (`ha='right'` at the left edge, `va='bottom'` at the top) instead.
- The "reaches the boundary" filter is `r > 0.9·R`, **not 0.65**. Every meridian
  converges at the poles, so a meridian on the invisible hemisphere still shows a
  sliver when a pole is in view, and its lowest visible point is that pole. Measured
  for `ortho(48N, 123W)`: genuine limb crossings bottom out at r/R = 0.996-1.001,
  far-side meridians at 0.672. 0.65 let all of them through and stacked four labels
  on the pole. Note the *fraction of visible track* does **not** separate the two
  populations (0.25-0.35 against 0.47-0.73) — the radius does.
- Labels keep **their own radius**; they are not snapped to the boundary circle.
  Snapping collapses every parallel along one meridian onto the same point.
- Longitude ticks are deduplicated modulo 360° (±180° is one meridian).
- Latitude labels that would collide with an already-placed label **slide along
  their own parallel** to the first clear point, which keeps them on the line they
  name. `lat_label_lon` overrides the choice of meridian; its default is the
  left-most point, *not* `center_lon + 90°` as once documented.

**Pseudocylindrical maps.** Longitude labels go where each meridian crosses the
parallel chosen by `xaxislocation` (which must be forwarded — it was silently
ignored for this family). Whether the bottom edge can carry labels depends on the
projection, so it is decided by **measuring the projected spacing**, not by the
projection name or by the latitude being near ±90°: Hammer, Mollweide and sinusoidal
converge to a point at the poles and fall back to the middle of the latitude range
(the equator on a whole-world map, matching m_map's `m_grid('xaxis','middle')`),
while Robinson has a pole *line* and keeps its bottom labels.
