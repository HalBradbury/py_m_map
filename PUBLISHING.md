# py_m_map — publication readiness

**Assessed:** 2026-08-05, against `py_m_map` 0.1.0.
Companion to `REVIEW.md` (code review) — that covered correctness; this covers
everything else standing between the current tree and a package someone else can
install and use.

**Where it stands.** The library is in good shape: 28 modules, 41 exported
functions, 14 projections, and the code review's defects are fixed with a 30-test
regression suite plus a pixel baseline over all 29 example figures.

**Every blocker below is now closed.** The package installs from a wheel into a
clean environment and draws a correct map with no data setup at all — verified by
building, installing into a fresh venv, and rendering from outside the source
tree. The one substantial piece of work remaining is the example gallery (S1).

Verified during this assessment:

- `python -m build` produces both wheel and sdist; the wheel carries all 28
  modules, the bundled topography and the licence, with a 6,200-character
  long_description.
- Installed into a fresh venv and run from `/private/tmp`: `m_proj` + `m_elev` +
  `m_coast` + `m_grid` render correctly, and `m_lldist` returns 73.03 km for 1° of
  longitude at 49°N (analytically 111.32·cos 49° = 73.0 km).
- `import py_m_map` works with cartopy unavailable — all cartopy imports are
  function-local, so it is only needed when coastlines are drawn.

---

## Blockers — all now closed

### B1. No licence — **done, with one caveat outstanding**

MIT, as decided. `LICENSE` added and declared in `pyproject.toml` via
`license = "MIT"` + `license-files`; it appears in the wheel as
`dist-info/licenses/LICENSE`.

The licence file also carries an acknowledgements section recording that
py_m_map is an independent re-implementation of Rich Pawlowicz's m_map, that no
m_map source or data is redistributed, and the ETOPO1 citation for the bundled
topography.

**Caveat, unchanged:** m_map's own licence terms are still not established — there
is no statement of them anywhere in this tree, and MIT was chosen without them.
Whether a derivative work may be MIT-licensed depends on those terms. This is the
one item on this page I cannot close for you; Rich Pawlowicz is in your
department, and a short conversation settles it.

### B2. `m_elev` and `m_etopo2` needed data outside the package — **done**

See D1 below for what was implemented.

### B3. Package metadata was a stub — **done**

`pyproject.toml` now carries `readme`, `license`, `license-files`, `authors`,
`keywords`, ten `classifiers`, an `[project.optional-dependencies] test` extra,
and a `[tool.pytest.ini_options]` section. `[project.urls]` is still empty — it
needs a repository URL, which I do not have (see D3).

Worth knowing: setuptools **silently** accepted `readme = "README.md"` while that
file did not exist, producing a wheel with an empty long_description and no error.
Only inspecting the built metadata caught it. Re-check after any metadata edit.

### B4. No README — **done**

`README.md` covers what the library is, the m_map relationship (including why the
`m_`-prefixed names are a deliberate choice), install, a runnable quick-start, the
data situation, a full function table, the projection list with what is *not* yet
ported, differences from m_map, and how to run and re-bless the test baselines.

### B5. Missing `MANIFEST.in` — **done** *(found while verifying)*

`tests/` is not an importable package, so setuptools omitted the entire test suite
from the sdist — the published source distribution could not be verified by anyone
who downloaded it. `MANIFEST.in` now ships the docs, the tests and the 30 baseline
PNGs, and prunes `tests/outputs/`.

---

## Should fix before publishing

### S1. The example gallery — **done**

Rebuilt on real data, as decided. Outcome:

| Example | Now |
|---|---|
| `sat_ex1` | Real OISST v2 SST, November 1999 — the same month the original mapped from Pathfinder AVHRR |
| `sat_ex2` | Real sea-ice concentration, September 2012 (record Arctic minimum) |
| `sat_ex4` | Repurposed: NE Pacific SST anomaly vs 1982–2011 — the 2013–15 "Blob". No open chlorophyll product exists to replace the original |
| `sat_ex5` | Unchanged appearance, but fetches its NCEP files instead of reading a local `DB/` directory that was never in the repo |
| `sat_ex3`, `sat_ex7` | **Deleted.** Aerial photo and SAR; no open substitute, and the synthetic stand-ins were meaningless |
| `sat_ex6` | Colourbar moved outside the frame — its labels were written over the slanted boundary |
| `sat_ex8` | Longitude ticks coarsened to 10′; the automatic labels collided at fontsize 14 in a half-width subplot |

The suite is now 57 tests. `tests/example_data.py` holds the dataset registry and
provenance; `py_m_map/_data.py` gained `fetch_data_file` (streams to a `.part` file
and renames on success, so an interrupted transfer cannot leave a truncated file
that later looks valid).

Verified: `sat_ex5` reproduces its baseline **exactly** after the swap — the LTM
files are bit-identical to the January average it previously computed from the full
monthly series (max difference 0.00000 m s⁻¹), which is what validated the whole
fetch approach before anything uncertain was touched.

Verified offline: with `HOME` pointed at an empty directory and
`PY_M_MAP_NO_DOWNLOAD=1`, all four data-dependent examples **skip** with actionable
messages rather than failing.

Three library defects surfaced while doing this, logged in `REVIEW.md`:

- **M9** — an `m_pcolor` masking trap that could paint over a whole figure.
  **Fixed**: off-map cells are now transparent rather than being sent through the
  colormap's "bad" colour, so a `set_bad` colour marks only the caller's own
  missing data. Needed matplotlib ≥ 3.5, now declared.
- **M10-M14** — five separate tick-label placement defects on non-rectangular
  projections, **all now fixed**: labels rendered upside-down, latitude/longitude
  collisions, parallels collapsed onto one radius, pseudocylindrical longitude
  labels stacked at the pole, and orthographic crowding from far-side meridians
  plus a duplicated ±180°. See `REVIEW.md` for each.

  This was the weakest area of the codebase, and they shared one root cause:
  labels were positioned at an extremum of the projected boundary
  (bottom-most, left-most), which is only well defined when that boundary is a
  rectangle. Circular and pseudocylindrical outlines have extrema that many
  gridlines share.

### S1b. Original assessment, for the record

This is the substantive quality issue. Eight of the 29 examples are built on
synthetic data, and four of those do not survive being looked at:

| Example | Problem |
|---|---|
| `sat_ex3` | "Synthetic aerial photograph" is three flat coloured rectangles. Conveys nothing. |
| `sat_ex7` | "Synthetic SAR" is grey noise with a diagonal ripple. Conveys nothing. |
| `sat_ex2` | "Synthetic ice cover" is a rainbow bullseye around the pole; also the coastline renders as faint grey fragments. |
| `sat_ex4` | "Synthetic chlorophyll" has visible rectangular blocks with hard edges — obviously not a data field. |

Two more have presentation defects rather than data defects:

- `sat_ex8` — two panels side by side with x tick labels overlapping into
  illegibility.
- `sat_ex6` — a stray colourbar clipped against the right edge.

For a published package the examples *are* the documentation, and these would be
the first thing a prospective user sees.

**Decision: rebuild around real data fetched and cached on demand.**

The obvious risk was that modern satellite archives mostly sit behind Earthdata
logins, which would make this impossible. I probed candidate endpoints before
committing. Results:

| Source | Status | Size |
|---|---|---|
| NOAA PSL — NCEP reanalysis LTM, `uwnd.10m` / `vwnd.10m` | open, no auth | 1.2 MB each |
| NOAA PSL — NCEP reanalysis LTM, `prate.sfc` | open, no auth | 1.2 MB |
| NOAA PSL — NCEP reanalysis LTM, `slp` | open, no auth | 0.6 MB |
| NOAA PSL — OISST v2 `sst.mnmean` | open, no auth | 64 MB |
| NOAA PSL — OISST v2 `icec.mnmean` (sea-ice concentration) | open, no auth | 64 MB |
| NOAA NCEI WOA18 | 404 at the path tried | — |
| NSIDC G02135 | 404 at the path tried | — |
| Ifremer Argo global index | open | 315 MB (too large) |

So the plan is viable on NOAA PSL alone, which is open, stable and unauthenticated.
Note the two OISST files are 64 MB each — fine as a one-off user download, too
heavy for routine CI, so examples depending on them should skip unless the file is
already cached or an opt-in variable is set.

Proposed mapping:

| Example | Becomes |
|---|---|
| `sat_ex1` global SST | real OISST v2 monthly SST on Hammer–Aitoff |
| `sat_ex2` sea ice | real OISST `icec` concentration, polar stereographic |
| `sat_ex3` "aerial photo" | **delete** — nothing to salvage |
| `sat_ex4` chlorophyll | **delete or repurpose** — no open chlorophyll source found |
| `sat_ex5` N Pacific winds | unchanged in appearance, but fetch the NCEP LTM files it currently reads from a local `DB/` directory (already verified available) |
| `sat_ex7` SAR | **delete** — nothing to salvage |
| `sat_ex6` Argo tracks | keep synthetic tracks (the Argo index is too large) but fix the clipped colourbar |
| `sat_ex8` shaded relief | keep; fix the overlapping tick labels |

Work required, in order:

1. A small fetch-and-cache helper in `py_m_map/_data.py` (stream to
   `~/.py_m_map/`, atomic rename, resume-safe, progress to stderr). This is the
   only new library code needed; everything else is example scripts.
2. `sat_ex5` first — it is a pure swap of a local path for a fetched one, so it
   validates the helper against a figure whose correct output is already known.
3. Then `sat_ex1` and `sat_ex2` on real fields.
4. Delete `sat_ex3`, `sat_ex7`, and `sat_ex4` unless a source turns up; remove
   their baselines.
5. Fix the `sat_ex6` and `sat_ex8` presentation defects.
6. Re-bless baselines; mark the network-dependent examples so the suite skips
   them cleanly when offline.

### S2. Eight examples cannot run on a fresh install

`example2, 3, 7, 14, 16, 17` and `sat_ex6` need `m_elev`/`m_etopo2` data; `sat_ex5`
loads NCEP reanalysis netCDF from a local `DB` directory that is not in this repo
at all. Whatever is decided in D1, the examples that depend on optional data
should skip cleanly with an explanatory message rather than fail.

### S3. No CI — **done**

`.github/workflows/tests.yml`, three jobs:

- **tests** — Python 3.10/3.11/3.12 against current dependencies, with
  `PY_M_MAP_SKIP_BASELINE=1`. Floating dependencies would fail the image
  comparison on antialiasing rather than on a real regression, so it is skipped
  here.
- **baseline** — Python 3.12 with `matplotlib==3.10.8` and `numpy==2.4.3`, the
  versions that rendered the committed references, running the full suite *with*
  image comparison. Uploads the difference panels as an artifact on failure.
- **package** — builds wheel and sdist, runs `twine check`, then asserts the
  distributions actually contain the bundled topography, the licence, a non-empty
  long_description and a testable `tests/` tree, and finally imports the installed
  wheel from outside the source tree and calls `m_elev` to prove the bundled data
  works with no setup.

Both 64 MB OISST downloads stay opt-in (`PY_M_MAP_FETCH_LARGE` unset), so CI does
not pull them; the examples needing them skip. Natural Earth, GSHHS and the small
NCEP files are cached between runs.

The YAML was validated and every non-trivial step was run locally rather than
trusted to a first push. That is how the two faults in S5 were found.

### S5. Faults the packaging checks found — **fixed**

Running the distribution checks locally, rather than after pushing, turned up two
things no other test would have caught:

- **The sdist was 12.5 MB**, because `MANIFEST.in` shipped the 30 baseline PNGs.
  Those references are specific to the stack that rendered them, so for anyone
  building from an sdist on a different matplotlib they would fail on antialiasing
  — shipping them was worse than useless. `tests/baseline/` is now pruned from the
  distribution and stays a repository/CI gate. Sdist is 0.30 MB, wheel 0.22 MB.
- **`sat_ex8` failed outright** from an sdist. It reads a local Barkley Sound DEM
  (`barkley_sound_1_navd88_2016.nc`) that is not in the repository and, unlike the
  other example data, has no stable open URL to fetch it from. It now resolves
  through the shared data path and skips with an explanation when absent, matching
  every other data-dependent example. It still runs where the file is present.

Verified end to end: extracting the sdist into a clean directory with an empty
`HOME` and `PY_M_MAP_NO_DOWNLOAD=1` gives 68 passed, 7 skipped, 0 failed.

### S4. Repository hygiene

Not a git repository yet. `.gitignore` has been added. Still in the tree and
probably should not be committed: `Py_M_Map.zip` (a stale 264 KB snapshot of the
package — it duplicates `py_m_map/` at an older revision), a stray root-level
`outputs/` directory containing one PNG, `.DS_Store` files, and `.pytest_cache/`.
I have not deleted any of these — they are yours to confirm.

---

## Nice to have

- **N1** — `py.typed` marker. **Deliberately not added.** I checked before
  shipping it: of the 41 public callables, **none** has a fully annotated
  signature, 12 have no parameter annotations at all, and only 20 declare a return
  type. `py.typed` is a promise that a package is typed; adding it here would make
  downstream type checkers silently infer `Any` throughout, which is worse than the
  honest absence of a marker. Annotate the public API first, then add it.
- **N2** — Docstrings are consistent NumPy style throughout, so a Sphinx or
  mkdocstrings API reference is mostly free. Worth doing if this is to be used by
  students who did not write it.
- **N3** — `EXAMPLES.md` is good and should become the gallery page of the docs
  rather than a loose file.
- **N4** — `CHANGELOG.md` — **done**. Written against the state of 0.1.0, since
  nothing has been published yet, and grouped by consequence (wrong output,
  crashes, label placement) rather than by module.
- **N5** — Consider whether `m_*` function names are wanted as the public API.
  They give exact m_map correspondence, which is the point of the port and is
  right for teaching; they are also unidiomatic for Python and will read oddly to
  anyone arriving from cartopy. My view: keep them — fidelity to m_map is the
  library's reason to exist — but say so explicitly in the README so it reads as
  a deliberate choice.

---

## Decisions taken

**D1. External elevation data — done.** Bundled 1° grid, ETOPO1 on demand.

`py_m_map/data/topo_1deg.npz` (108 KB) was generated by block-averaging the local
ETOPO1 ice-surface grid to 1°, giving the 180×360 array `elevation.py` already
expected. ETOPO1 is a US Government work, so this sidesteps the question of
redistributing m_map's `m_topo.mat` entirely.

It is a faithful drop-in — cross-checked against `m_topo.mat`:

| Metric | Value |
|---|---|
| Mean difference | +0.3 m |
| Median difference | +0.1 m |
| RMS difference | 8.0 m |
| Land/ocean sign agreement | 99.95 % |
| Correlation | 1.00000 |

`m_elev` now loads the bundled grid by default — deliberately *in preference to*
any `m_topo.mat` beside the package, so the same code gives the same figure on
every machine. `PY_M_MAP_TOPO_FILE` overrides it for exact MATLAB parity.

The switch moved three figures (`example2` 1.75 %, `example3` 2.58 %,
`example14_one_ocean` 3.73 % of pixels). The baseline check caught all three; each
diff is thin filaments along contour edges, which is what an 8 m grid change
produces. Inspected and re-blessed.

`m_etopo2` still needs the full 447 MB ETOPO1 and resolves it through
`py_m_map/_data.py`: `$PY_M_MAP_DATA_DIR`, then `~/.py_m_map/`, then the legacy
package-relative path. When absent it warns with every location searched plus the
download URL, and falls back to the bundled 1° grid.

**D2. Example gallery — decided, not yet built.** Rebuild around real fetchable
data. See S1 for the plan and the endpoints I verified.

**D3. Still open.** I have not checked whether `py_m_map` is free on PyPI, and
`[project.urls]` is empty because I do not have a repository URL. `authors` carries
your email only — add your name if you want it attributed. The `LICENSE` copyright
line reads "py_m_map contributors" rather than a personal name; change it if you
prefer.
