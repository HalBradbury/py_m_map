# Changelog

All notable changes to py_m_map are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[semantic versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

First public release preparation. Nothing has been published to PyPI yet, so the
entries below describe the state of 0.1.0 rather than changes against a previous
release. `REVIEW.md` carries the full detail for each defect, with the failure it
produced and how it was verified.

### Fixed — wrong scientific output

These produced a plausible-looking but incorrect figure or number, with nothing to
signal it.

- `m_landmask` reported enclosed water as land. Polygon interior rings were
  ignored, so lakes and inland seas — the Caspian above all — came back as land,
  silently corrupting any mask, average or statistic over such a region.
- Discrete contour colourbars were drawn as continuous gradients, so the bar no
  longer described the figure it annotated. The discrete/continuous choice now
  considers the plotted artist as well as the colormap, and the band colormap is
  resampled when needed.
- `m_contfbar` took its colours from `m_contourf`'s black contour-line overlay
  rather than the filled bands, giving an all-black colourbar to anyone relying on
  the default `colormap=None`.
- The pseudocylindrical lobe offset (`x_offset`) leaked between `m_proj` calls and
  was added to every subsequent transform, displacing an entire map.
- Oblique Mercator's forward transform folded quadrants through `arctan`, making it
  non-invertible: `m_xy2ll` returned the antipode. Round-trips are now exact to
  ~1e-14.
- `m_pcolor` sent off-map cells through the colormap's "bad" colour, the same
  channel as the caller's own missing data. With an opaque `set_bad`, a call whose
  data lay entirely off the map painted over the whole figure.

### Fixed — crashes

- `m_etopo2` raised on any region crossing the antimeridian. The straddle test ran
  *after* a modulo wrap that made it unreachable, leaving the two-piece read as
  dead code and handing the contiguous path a negative array width.
- `m_xy2ll` raised `TypeError` for oblique projections: a bare forward closure was
  stored where a `pyproj`-compatible callable was expected.
- `m_proj('lambert' | 'albers', ...)` raised `CRSError` for any latitude range
  symmetric about the equator, because the standard parallels summed to zero.
- `m_ll2xy` raised `TypeError` on scalar input under a lobed projection — for
  in-range points too, so the plain-float call a student would write failed
  immediately.
- `m_proj('azimuthal_equal_area')` with underscores resolved to a non-existent
  projection and reported the wrong name in the error.
- Oblique projections divided by zero for a latitude limit on the equator.

### Fixed — tick label placement

Every projection family whose boundary is not a rectangle had a placement defect.
They shared one root cause: labels were positioned at an extremum of the projected
boundary (bottom-most, left-most), which is only well defined for a rectangle.

- Circular-grid labels were rotated tangentially, which is forced to ±90° at the
  left and right extremes, so one side read upside-down. Labels are now horizontal
  and anchored away from the boundary.
- Latitude and longitude labels collided on polar maps, and parallels were snapped
  to a shared radius. Each label now keeps its own radius, and a latitude label
  that would collide slides along its own parallel to the first clear point.
- Pseudocylindrical longitude labels all stacked at the pole, where every meridian
  converges. They are now placed on a parallel chosen by `xaxislocation` — which
  was previously accepted and silently ignored for this projection family — with a
  fallback measured from the projected spacing, so Robinson's pole *line* keeps its
  bottom labels while Hammer and Mollweide use the equator.
- Orthographic maps labelled meridians on the invisible hemisphere, stacking them
  on the visible pole, and labelled ±180° twice.

### Changed

- **Distribution.** Added `LICENSE` (MIT), `README.md`, `CHANGELOG.md`,
  `.gitignore` and `MANIFEST.in`; filled in author, licence, readme, keywords,
  classifiers and a `test` extra. `cartopy` is now declared — it was imported at
  runtime by `m_coast`, `m_gshhs*` and `m_usercoast` but absent from the
  dependencies, so an installed package could not draw a coastline. matplotlib is
  floored at 3.5 for per-cell alpha support.
- **Bundled topography.** `m_elev` previously read `m_topo.mat` from a MATLAB m_map
  installation beside the source tree, so it was dead for anyone who installed the
  wheel. A 108 KB 1° grid derived from ETOPO1 now ships in the package and
  `m_elev` works with no setup; it matches the original to 8 m RMS
  (correlation 1.00000). `PY_M_MAP_TOPO_FILE` overrides it.
- **External data resolution.** `m_etopo2` and the examples locate optional data
  through `$PY_M_MAP_DATA_DIR`, then `~/.py_m_map/`, then the legacy paths, and
  report every location searched when a file is missing.
- **Example gallery rebuilt on real data.** The satellite examples used synthetic
  fields; they now fetch open NOAA products (OI SST v2, NCEP reanalysis) on first
  use and cache them. `sat_ex3` and `sat_ex7` were deleted rather than left as
  meaningless stand-ins, and `sat_ex4` was repurposed to the NE Pacific SST
  anomaly. Examples whose data cannot be reached skip with an explanation.
- `xticklabels` / `yticklabels` accepted custom label text and silently discarded
  it; `xlabeldir` was accepted and never read. Both now warn, and the docstrings
  say what is actually supported.

### Added

- `tests/test_regressions.py` — 48 assertion-based tests, one per defect above.
  The pre-existing example tests contain no assertions at all.
- An image-baseline check in `tests/conftest.py`: every PNG an example writes is
  compared against `tests/baseline/` at zero pixel tolerance, with a
  baseline/current/difference panel written on failure. This caught two regressions
  introduced while fixing the defects above, both of which the test suite passed.
- GitHub Actions workflows for the test matrix, the pinned-stack image comparison,
  and distribution checks.

### Known limitations

- `m_coast` still fills lakes with the land colour; only the *mask* handles holes.
- Custom tick label text and `xlabeldir` are unimplemented (they warn).
- 7 of 21 m_map projections are not ported; see `IMPLEMENTATION_PLAN.md`.
- `sat_ex8` needs a local Barkley Sound DEM that has no stable open URL, and skips
  without it.
- The package is not typed: no public function has a fully annotated signature, so
  no `py.typed` marker is shipped.
