# py_m_map — Code Review

**Date:** 2026-08-05
**Scope:** all 27 modules of `py_m_map/` (~8,400 lines), the 29 files in `tests/`,
`pyproject.toml`, `IMPLEMENTATION_PLAN.md`, `EXAMPLES.md`.
**Method:** six independent reviewers over module slices, each finding then put
through an adversarial refutation pass (24 raised, 4 refuted, 20 surviving). The
seven high-severity findings were then re-verified by hand, by running them.

**Confidence labels used below**

| Label | Meaning |
|---|---|
| **Reproduced** | I ran it and observed the failure; the transcript is quoted. |
| **Traced** | Confirmed by reading the code path; not executed (e.g. needs absent data). |
| **Reported** | Surfaced by a reviewer and survived refutation, but not independently re-run. |

---

## Resolution status

All eight high-severity findings and five of the eight medium ones are fixed, with
assertions in `tests/test_regressions.py` (30 tests) pinning each one. Two further
defects were uncovered *while* fixing and verifying these — both are in the list.

| # | Finding | Status |
|---|---|---|
| H1 | `m_landmask` reports enclosed water as land | **Fixed** |
| H2 | ETOPO1 antimeridian straddle branch unreachable | **Fixed** |
| H3 | Discrete contour colourbars rendered as gradients | **Fixed** |
| H4 | Lambert/Albers reject equator-symmetric ranges | **Fixed** |
| H5 | `x_offset` leaks between `m_proj` calls | **Fixed** |
| H6 | Oblique Mercator has no inverse | **Fixed** |
| H7 | `m_ll2xy` crashes on scalar input under a lobed projection | **Fixed** |
| H8 | cartopy undeclared | **Fixed** |
| H9 | Oblique forward folded quadrants — inverse returned the antipode | **Fixed** (found during H6 verification) |
| H10 | `m_contfbar` took its colours from the black contour-line overlay | **Fixed** (found during H3 verification) |
| M1 | Custom tick label text silently ignored | **Partly** — now warns; values still unsupported |
| M2 | `xlabeldir` dead parameter | **Partly** — now warns; still unimplemented |
| M3 | `center_lat`/`center_lon` leak | **Fixed** |
| M4 | Polygon holes unrendered (as distinct from unmasked) | **Open** — see below |
| M5 | `azimuthal_equal_area` underscore spelling misroutes | **Fixed** |
| M6 | Oblique divide-by-zero at the equator | **Fixed** |
| M7 | `shading` docstring backwards | **Fixed** |
| M8 | No test asserts anything | **Fixed** for the above; examples still assertion-free |
| L1-L6 | Housekeeping | L2, L3, L5 **fixed**; L1, L4, L6 **open** (cosmetic) |

**Verification.** The 29 example figures were rendered before and after and
compared pixel by pixel. 27 are byte-identical. The three that changed are the
intended improvements, each inspected at magnification:

- `example7.png` — the colourbar now shows the 22 discrete bands its contourf
  actually draws, in the correct topographic colours, instead of a smooth ramp.
- `example15_inverse.png` — three small patches, one per subplot, all at the
  Caspian Sea: it is now correctly water rather than coloured land data.
- `example5.png` — canvas 1 px wider; the overlapping content is pixel-identical.
  The oblique forward fix is a pure translation of the projected coordinates, so
  the rendered map is unchanged.

**Why M4 is still open.** Hole *rendering* needs the same treatment in four
divergent code paths (`_draw_patch`, `_draw_patch_oblique_clip`,
`_draw_patch_geographic_clip`, `_draw_patch_circular`), each with its own
clipping, antimeridian splitting and projection order, and `ax.fill` cannot
express holes — every site needs a compound `PathPatch`. Threading interior rings
through the cut-meridian ring-splitting logic is the hard part. Doing it in three
of four places would be worse than not starting; it deserves its own pass. The
numerical consequence (masking) is fixed, so what remains is cosmetic: a lake is
drawn in the land colour.

**Why M1/M2 are only partly done.** Supporting custom label text means threading
a label sequence through all five projection renderers, and for circular frames
labels are placed at boundary intersections where "tick order" is not well
defined. That is a feature, not a bug fix. The actual defect was the *silence* —
both now warn, and the docstrings say what is supported.

---

## Verdict

The port is architecturally sound — the projection state machine, the grid
dispatch by projection type, and the geodesic maths are all in good shape, and
the breadth of coverage (40 exported functions, ~20 projections) is genuinely
impressive. But it is not yet safe to teach with unmodified.

Seven high-severity defects are confirmed. The dominant risk is not the crashes
— those announce themselves — it is the three defects that **silently produce a
wrong scientific figure**: `m_landmask` misclassifying enclosed water as land,
discrete colorbars rendered as continuous gradients, and a projection offset
that leaks between `m_proj` calls and corrupts every subsequent coordinate.
Students will trust these outputs.

The aggravating factor is that **the test suite contains zero assertions**. All
29 test files render a PNG and check nothing about it. During a clean run,
`test_example9` passed while its GSHHS download 404'd and coastlines were
silently omitted from the figure — a demonstration that the suite passes on
blank maps. Every defect below was invisible to CI, and so will every fix be
until assertions exist.

---

## Strengths

- **`geodesic.py` is correct.** Spherical inverse/forward formulations are right
  and the unit conventions match m_map (`m_lldist` in km, `m_idist` in metres).
- **Projection state machine scales well.** Switching projections without
  recreating state is efficient, and the alias/prefix resolution handles ~20
  projection variants.
- **`grid.py` separates concerns cleanly** by projection type (rectangular /
  circular / conic), with consistent tick and label dispatch — impressive for a
  1,788-line module.
- **Natural Earth polygon rendering is correct for simple polygons**; exterior
  ring handling, antimeridian splitting, and the pseudocylindrical cut-meridian
  ring splitting are all well thought through and well documented.
- **`IMPLEMENTATION_PLAN.md`'s architectural notes are genuinely valuable** —
  the gradient-direction, data-orientation, and zorder conventions are exactly
  the things a maintainer needs written down.

---

## High severity

### H1 — `m_landmask` reports enclosed water as land · **Reproduced**

`coast.py:658`

`_add_parts` builds its point-in-polygon paths from `poly.exterior.coords` and
never looks at `poly.interiors`. Points inside a hole — a lake, an inland sea —
are tested against the outer boundary only, and come back as land.

This is a genuine holes bug, not a quirk of the dataset. The Natural Earth 110 m
land polygon enclosing (52°E, 41°N) has exactly one interior ring; the point
lies inside it; Shapely's own `contains` returns `False`:

```
Caspian Sea (52E,41N)  -> m_landmask says land=True
  n_interiors=1  inside_exterior=True  shapely_contains=False
  -> point lies inside interior ring #0  (a genuine HOLE)
```

**Impact:** any masking, averaging, or statistic computed over a region
containing a lake or inland sea is wrong, with no warning.

**Fix:** test exterior AND NOT any interior. Either use Shapely's
`prepared.contains` directly, or build the matplotlib `Path` with the interior
rings included and `Path.contains_points` will honour the even-odd rule.

---

### H2 — ETOPO1 crashes on any antimeridian-crossing region · **Traced**

`etopo.py:72-83`

`col_start` and `col_end` are wrapped modulo `_NX` at lines 72-73, *before* the
straddle test `if col_end > _NX:` at line 83. After a modulo the value is always
in `[0, _NX)`, so **that test can never fire and the entire two-piece
antimeridian read at lines 83-99 is unreachable dead code.** Execution falls to
the contiguous branch with a negative width:

```
request 170°E .. 190°E:
  before wrap: col_start=20999 col_end=22201  (_NX=21600) -> straddle? True
  after  wrap: col_start=20999 col_end=601                -> straddle? False
  nlng = col_end - col_start + 1 = -20397
  -> np.empty((nlat, -20397)) : negative dimensions are not allowed
```

The ETOPO1 binary is present on this machine, so this is live: any Bering
Strait, Fiji, or New Zealand dateline map hits it.

**Fix:** perform the straddle test on the unwrapped indices, before the modulo.

---

### H3 — Discrete contour colorbars render as continuous gradients · **Reproduced (code fact)**

`colorbar.py:221`

```python
render_continuous = (len(clevel) > 50) or (n_cmap_colors > 50)
```

The `or` makes the colormap's resolution sufficient on its own. Any standard
256-colour map (viridis, and every `m_colmap` output) forces continuous
rendering, so a 5-level `m_contourf` gets a smooth ramp instead of five bands —
the colorbar no longer describes the figure it annotates.

**Fix:** `and`. Continuous rendering is only appropriate when the levels *and*
the colormap are both fine-grained.

---

### H4 — Lambert / Albers reject latitude ranges symmetric about the equator · **Reproduced**

`projection.py:130`

Standard parallels are computed as `lat_1 = lat_mid - span/6`,
`lat_2 = lat_mid + span/6`. When the range is symmetric about the equator,
`lat_mid == 0`, so `lat_1 + lat_2 == 0`, which Proj rejects:

```
m_proj('lambert', lon=[-180,180], lat=[-60,60])
→ CRSError: +proj=lcc +lat_1=-20.0 +lat_2=20.0 ... :
  lcc: Invalid value for lat_1 and lat_2: |lat_1 + lat_2| should be > 0
```

**Fix:** when `|lat_1 + lat_2|` is near zero, nudge both parallels by a small
offset so the sum is non-zero, at negligible cost in distortion.

---

### H5 — `x_offset` leaks between `m_proj` calls and corrupts all coordinates · **Reproduced**

`projection.py:307`, applied at `projection.py:675-676`

The pseudocylindrical branch sets `state.x_offset` to shift a lobe's central
meridian. Only three branches ever reset it (lines 307, 560, 605); every other
projection inherits whatever the previous call left behind, and lines 675-676
then add it to every transform.

The offset is only non-zero for an off-centre lobe, so the reproduction needs
one (with the full `lon=[-180,180]` the mid-longitude is 0 and nothing leaks):

```
m_proj('mollweide', lon=[0,180], lat=[-90,90])  → x_offset = 9,009,950.4
m_proj('mercator',  lon=[-180,180], lat=[-80,80]) → x_offset STILL 9,009,950.4
m_ll2xy(0, 0) → x = 9,009,950   (should be 0)
```

**Impact:** silent, whole-map coordinate corruption in any session that uses a
lobed Mollweide or sinusoidal projection and then switches projection without
`reset_state()`.

**Fix:** reset the projection-dependent state fields at the top of `m_proj`.
The same treatment fixes M3 (`center_lat` / `center_lon` persistence).

---

### H6 — Oblique Mercator has no inverse transform · **Reproduced**

`projection.py:370`

The oblique branch assigns a bare Python closure `_oblique_fwd` to `state.proj`,
but `m_xy2ll` (line 735) invokes `state.proj(x, y, inverse=True)`:

```
m_proj('oblique', lon=[-130,-120], lat=[45,50])
m_xy2ll(0, 0)
→ TypeError: _oblique_fwd() got an unexpected keyword argument 'inverse'
```

`m_xy2ll` is therefore completely unavailable for oblique projections, and so is
anything built on it.

**Fix:** wrap the forward and inverse closures in a small callable that accepts
and dispatches on `inverse=`, matching the `pyproj.Proj` interface the rest of
the module assumes.

---

### H7 — `m_ll2xy` crashes on scalar input under a lobed projection · **Reproduced** *(found during verification; not in the original review)*

`projection.py:676` → `projection.py:706`

`x = x + state.x_offset` demotes a 0-d ndarray to a `np.float64` scalar, which
does not support item assignment. Line 706 then attempts exactly that:

```
m_proj('mollweide', lon=[0,180], lat=[-90,90])
m_ll2xy(90.0, 0.0)   → TypeError: 'numpy.float64' object does not support item assignment
m_ll2xy(np.array([90.0]), np.array([0.0]))   → works
```

It fails for an **in-range** point, so this is not an edge case — the plain-float
call a student would naturally write fails immediately.

**Fix:** normalise to at least 1-D with `np.atleast_1d(np.asarray(..., float))`
before the offset is applied.

---

### H8 — cartopy is required at runtime but undeclared · **Reproduced**

`pyproject.toml:10-17`

`coast.py:67`, `coast.py:619`, `gshhs.py:34` and `usercoast.py:126` all import
cartopy, and `cartopy` appears nowhere in `dependencies`. A `pip install .` into
a clean environment produces a package whose coastline functions — the most
basic thing the library does — raise `ImportError`.

**Fix:** declare it.

---

## Medium severity

### M1 — Custom tick label lists are silently ignored · **Reported**

`grid.py`

`xticklabels` / `yticklabels` are documented as accepting a list, but only their
truthiness is honoured; the values are discarded and the auto-formatted labels
drawn instead. `m_grid(xtick=[90,180,270], xticklabels=['West','Mid','East'])`
renders `90°E`, `180°E`, `270°E`. Either implement the values or document that
the parameter is on/off only.

### M2 — `xlabeldir` is a dead parameter · **Reported**

Accepted, documented, never read.

### M3 — `center_lat` / `center_lon` persist across `m_proj` · **Reported**

Same root cause as H5; fixed by the same state reset.

### M4 — Polygon holes are unrendered as well as unmasked · **Reported**

The H1 root cause also affects drawing: a lake inside a landmass is filled with
the land colour rather than left as water.

### M5 — `azimuthal_equal_area` with underscores misroutes · **Reported**

`projection.py:59` tests for `'equal-area'` and `'equal area'` but not
`'equal_area'`, so the underscore spelling falls through to prefix matching,
resolves to a non-existent `azimuthal_equidistant`, and reports *that* name in
the error — misdirecting the user to the wrong projection.

### M6 — Oblique projection divides by zero at the equator · **Reported**

`projection.py:336`: `np.tan(r1)` is zero when the latitude limit is 0°.
Completes with a `RuntimeWarning` and an infinite intermediate.

### M7 — The `shading` docstring is backwards · **Reported**

`pcolor.py` describes centre/edge coordinate semantics the wrong way round,
inviting users to pass edges where centres are expected.

### M8 — No test asserts anything · **Reproduced**

Zero `assert` statements across all 29 test files. See the verdict above.

---

## Found later, while rebuilding the examples (2026-08-05)

These all surfaced from *using* the library rather than reading it — none was
caught by any reviewer, and none would have been found by reading `grid.py` or
`pcolor.py` in isolation.

Tick-label placement on non-rectangular projections turns out to be the weakest
area of the codebase. Every projection family whose boundary is not a rectangle
has a placement defect, and they share one root cause: **labels are positioned at
an extremum of the projected boundary (bottom-most, left-most), which is only
well defined when the boundary is a rectangle.** On a circle the extremum is a
single point shared by many gridlines; on a pseudocylindrical outline it is a pole
where every meridian converges.

| # | Defect | Status |
|---|---|---|
| M9 | `m_pcolor` masking trap can paint over a whole figure | **Fixed** |
| M10 | Circular-grid labels rendered upside-down on one side | **Fixed** |
| M11 | Latitude/longitude labels collide on polar maps | **Fixed** |
| M12 | Latitude labels collapse onto one radius | **Fixed** |
| M13 | Pseudocylindrical longitude labels all stack at the pole | **Fixed** |
| M14 | Orthographic labels crowd: far-side meridians, duplicate ±180°, collisions | **Fixed** |
| M15 | Ruler-box corners ignored whether a tick lands on them | **Fixed** |

Circular and pseudocylindrical tick labels are now verified collision-free across
orthographic, azimuthal equal-area and stereographic at two cap radii, and spread
across hammer, robinson, mollweide and sinusoidal — see
`test_circular_grid_labels_never_overlap`,
`test_ortho_does_not_label_the_far_hemisphere` and
`test_pseudocylindrical_longitude_labels_are_spread_out`.

### M9 — `m_pcolor` masks the data, so an out-of-range call can paint over the map · **Fixed**

`pcolor.py`

`m_pcolor` funnelled three unrelated things into one channel — `data = NaN`:

1. cells outside the map boundary,
2. cells straddling the projection's cut meridian,
3. missing values in the caller's own data.

All three then went through the colormap's "bad" colour. With matplotlib's default
that colour is transparent, so nothing looked wrong; set an opaque one — grey land,
say — and every off-map cell is painted too. A call whose data lies *entirely* off
the map covers the whole figure.

**Failure:** on a Hammer-Aitoff centred at 150°W with `cmap.set_bad('white')`,
drawing a global field and then a second copy shifted by −360° (the idiom m_map's
own satellite example 1 uses) produced a blank white ocean — the correct first
field painted over by the fully-masked second one. Diagnosed by inspecting the
artists: two QuadMeshes, the second with a 100 % masked array.

**The fix originally suggested here does not work.** "Mask the coordinates" is
impossible: matplotlib rejects them outright —

> `ValueError: x and y arguments to pcolormesh cannot have non-finite values or be
> of type numpy.ma.MaskedArray with masked values`

— verified against matplotlib 3.10.8 before committing to an approach.

**Fix as applied:** off-map and cut-straddling cells are made transparent with a
per-cell `alpha` array, which separates cases 1-2 from case 3. Those cells vanish
whatever the colormap says, while the caller's own NaNs still render as "bad".
They are additionally set to NaN so they take no part in colour autoscaling, and a
caller-supplied `alpha` is still honoured for the visible cells. No alpha array is
attached when nothing is clipped, so existing figures are untouched — confirmed by
all 27 example baselines being byte-identical after the change.

Requires `Collection.set_alpha` to accept an array; `pyproject.toml` now floors
matplotlib at 3.5 for that reason.

Covered by four tests, including one that reproduces the original two-mesh
satellite-example-1 failure and asserts the off-map mesh is wholly transparent.

### M10 — Circular-grid labels rendered upside-down on one side · **Fixed**

`grid.py:_place_label`

My first description of this was wrong in its diagnosis, though not its symptom.
The normalisation into (−90°, 90°] *was* already present — matplotlib's
`get_rotation()` simply reports −90° as 270°, which made it look absent.

The real cause is that the labels were rotated **tangentially**, and a tangent is
forced to exactly ±90° at the left and right extremes of a circle. No
normalisation can reconcile those two: the right-hand label reads bottom-to-top
and the left-hand one top-to-bottom, so the left one looks inverted. There is no
rotation rule that is both continuous around the circle and never upside-down —
which is why the original suggestion (normalise harder) could not have worked.

**Was:** `m_proj('azimuthal equal-area', lat=90, lon=0, radius=47)` +
`m_grid()` rendered the left-hand `90°W` reading downwards.

**Fix:** labels are now horizontal. What the rotation was also achieving —
keeping text clear of the boundary — is recovered by anchoring each label on the
side facing the map (`ha='right'` at the left edge, `va='bottom'` at the top, and
so on) so it grows outward. This matches matplotlib's own polar tick-label
convention and removes the whole defect class rather than shifting it.

Covered by `test_circular_grid_labels_are_never_inverted`, which asserts every
label's rotation lies in (−90°, 90°] across three circular projections. Verified
to fail on revert. Improved `example3`, `example8` and `sat_ex2`, whose small
rotated labels were hard to read even where not inverted.

### M11 — Latitude and longitude labels collide on polar maps · **Fixed**

`grid.py:1391-1420`

Distinct from M10, and the larger part of why `sat_ex2`'s left edge was
illegible: what looked like one inverted label was **two labels on top of each
other**. Separating longitude-only and latitude-only renders confirmed it.

With `lat_label_lon=None` (the default) each latitude label goes at its parallel's
left-most point on the boundary. On a polar map that point lies on the meridian
90° from the projection centre — exactly where that meridian's own label is
placed. So `90°W` and `50°N` are drawn at the same spot.

**Fix, in two parts.** Most of it fell out of M12: once each parallel keeps its
own radius instead of being snapped to the boundary, an inner parallel's label is
nowhere near the meridian label on the boundary, and the azimuthal case became
collision-free with no further work.

What remained was the genuinely irreducible case — a parallel that *does* reach
the boundary meets it exactly where the left-most meridian's label sits (50°N on a
40°-radius cap, or the equator on an orthographic). For that,
`_draw_grid_circular` now records the position of every label it has drawn and, for
latitude labels, walks rightwards along the parallel to the first point clear of
them. Sliding along the parallel keeps the label on the line it names, which
displacing it radially or by a fixed azimuth would not.

The `lat_label_lon` docstring was also corrected — it claimed a default of
`center_lon + 90°`, which the code has never implemented. `sat_ex2` keeps its
explicit `lat_label_lon=-75.0`, which is now a presentational preference rather
than a workaround.

### M15 — Ruler-box corners ignored whether a tick lands on them · **Fixed** *(a regression I introduced)*

`grid.py:_draw_ruler_corner`

The `boxstyle='line'` corner has two rules, not one, and which applies depends on
whether a grid tick falls exactly on the corner:

| at the corner | corner box | half-line to the diagonal |
|---|---|---|
| tick present | delimited by a separator; a fresh box continuing the alternation | drawn when the neighbouring strip is **empty** |
| no tick | not delimited; the neighbour's style runs on into it | drawn when that strip is **full** |

The condition inverts between them. Early in this work I was told "a line to the
diagonal if the box next to it is empty, and no line if the box next to it is
full" and applied it to *every* corner. That is right only where ticks land on
both edges — which on `sat_ex5`'s frame is the bottom-left corner and nowhere
else, exactly the one corner that still looked right afterwards.

**Failure:** `m_proj('miller', lon=[100, 260], lat=[0, 65])` with
`m_grid(box='fancy', boxstyle='line')`. Longitude ticks fall every 25° from 100°,
so one lands on the left edge but none on the right (250 + 25 > 260); likewise for
latitude. Three of the four corners were therefore wrong — a stub where there
should be none at top-right and bottom-right, and a missing continuation of the
left/right centre line at top-left and top-right.

**Diagnosis note.** `IMPLEMENTATION_PLAN.md` had described both branches correctly
from the start. Had I read it before changing the code, the over-generalisation
would have been obvious — the plan is the design record, and contradicting it
should have been a signal to check rather than proceed.

Covered by `test_ruler_box_corner_follows_the_tick_rule`, which pins all eight
colour/tick combinations plus two mixed cases. Affected `sat_ex5`, `example6` and
`example15_inverse` — the three figures using this box style.

### M12 — Latitude labels collapse onto one radius along an explicit meridian · **Fixed**

`grid.py:_place_label`

Found in my own output while checking the M10 fix, which is the only reason it was
caught at all. `_place_label` projected every label out to the boundary circle.
That is harmless for labels derived from a boundary crossing — it just absorbs
interpolation error — but with `lat_label_lon` set, every parallel shares one ray,
so all the latitude labels were snapped to the same point. `lat_label_lon` was
therefore unusable for more than one parallel, which is most of the time.

**Was:** `m_grid(lat_label_lon=-75)` on a 40°-radius polar stereographic put
`50°N` and `60°N` at an identical position.

**Fix:** `_place_label` takes `snap_to_boundary`, and the explicit-meridian branch
passes `False` so each label keeps its own radius (`60°N` at 0.75 R, `50°N` at
0.85 R). Covered by
`test_circular_latitude_labels_do_not_collapse_onto_each_other`.

### M13 — Pseudocylindrical longitude labels all stack at the pole · **Fixed**

`grid.py:_draw_grid_pseudocylindrical`

Longitude labels were placed where each meridian crosses `lat_min`. On a
whole-world Hammer, Mollweide, sinusoidal or Robinson map that is the south pole,
where *every* meridian converges — so all the labels were drawn on top of one
another at x ≈ 0.

**Was:** example 11 (Hammer centred on 170°E) drew `90°W`, `0°E` and `90°E` all at
x ≈ 8·10⁻¹⁰ m, y = −9.82·10⁶ m, overlapping each other and the caption beneath the
map. Visible in the previous `tests/outputs/example11.png`.

`xaxislocation` was also silently ignored for this projection family — it was never
passed through from `m_grid` — so `'middle'` could not be used to work around it.

**Fix:** labels are placed on the parallel selected by `xaxislocation`, which is
now forwarded. When the requested parallel is within 1° of a pole the middle of
the latitude range is used instead, since a converged boundary cannot carry
labels; for a whole-world map that is the equator, which is what m_map's own
Hammer examples select with `m_grid('xaxis','middle')`.

### M14 — Orthographic labels crowd near the visible pole · **Fixed**

`grid.py:1368-1386`

Three separate faults, all visible at once with
`m_proj('ortho', lat=48, lon=-123)` + `m_grid()`. Map radius R = 6.371·10⁶ m:

1. **Far-side meridians are labelled.** From a centre at 48°N/123°W the visible
   hemisphere spans roughly 147°E to 33°W, so 0°E, 30°E, 60°E and 90°E are all on
   the invisible side. But every meridian converges at the poles, and the north
   pole is only 42° from the centre — therefore visible. Each of those four
   meridians has a sliver of visible track near the pole, so each gets a label,
   and all four land at the projected pole: x ≈ 0.01·10⁶, y = +6.63·10⁶ m. The
   `r > 0.65·R` guard meant to reject meridians that do not reach the boundary
   passes because sin 42° = 0.669, just over the threshold.
2. **±180° is labelled twice.** `180°W` and `180°E` are the same meridian and are
   drawn at the identical point (−5.02·10⁶, −4.32·10⁶). The tick list contains
   both −180 and +180.
3. **Longitude and latitude labels collide**, as in M11 but on a non-polar
   circular map: `150°E` and `0°N` are placed 0.6 % of R apart.

**Fix.** The guard's *intent* was already right — "meridian doesn't reach the map
boundary" — its threshold was simply too loose, and 0.672 squeaked past 0.65. The
measured gap between the two populations is wide (0.672 against 0.996+), so the
threshold moved to 0.9 R, which separates them with margin. Ticks are now
deduplicated modulo 360° so ±180° is labelled once. The third fault is the same
collision handling as M11.

Result for `ortho(48N, 123W)`: 17 labels down to 12, with no overlaps and every
near-side meridian retained. Note the fix came from *measuring* both populations
rather than reasoning about visibility fractions — the fraction of each meridian's
track that is visible (0.25-0.35 for far-side against 0.47-0.73 for near-side) does
**not** separate them cleanly, so a plausible-sounding arc-length test would have
been unreliable.

---

## Low severity

- **L7** — `m_proj`'s `lon` argument is inconsistent across the pseudocylindrical
  family: `hammer` and `robinson` accept a scalar centre longitude, while
  `mollweide` and `sinusoidal` reject it and demand
  `lon=[lon_min, lon_max]`. Nothing in the projection type warrants the
  difference, and the error only appears at call time. Found while writing the
  M13 regression test.
- **L1** — `grid.py`'s `diag_offset_y` corner-rasterisation mechanism is
  implemented and documented but never invoked with a non-zero value.
- **L2** — `pcolor.py` emits a non-monotonic-coordinate warning that is expected
  and harmless for curvilinear projections; it alarms students about correct output.
- **L3** — `shaded_relief.py:229` likewise warns about uneven Y spacing that is
  an inherent property of the projection.
- **L4** — `py_m_map.egg-info/SOURCES.txt` lists 8 of 27 modules (stale; harmless,
  since `packages.find` auto-discovers).
- **L5** — `IMPLEMENTATION_PLAN.md` claims cartopy is declared (it is not) and
  still lists "No unit test suite" under Known Limitations despite `tests/`.
- **L6** — No `README`, no `.gitignore`; `Py_M_Map.zip`, `.DS_Store` files and
  `.pytest_cache/` are committed in the tree.

---

## Cross-cutting themes

1. **Silent wrong output is the dominant risk.** H1, H3, H5 and M4 all yield a
   plausible-looking figure or a confident wrong number. These matter far more in
   a teaching context than the crashes, which at least announce themselves.

2. **State is reset nowhere.** `m_proj` mutates a module-level singleton and no
   branch clears the fields it does not itself set. H5 and M3 are the same bug
   seen through two fields; more will appear as projections are added. A single
   reset at the top of `m_proj` closes the whole class.

3. **Scalar-versus-array input is not handled uniformly.** H7 is one instance;
   the codebase mixes bare arithmetic, `np.asarray`, and in-place masking on
   values that may be 0-d.

4. **Parameters were stubbed and abandoned.** M1 and M2 are documented features
   that do nothing, with no warning to the caller — worse than absent, because
   the docstring promises them.

5. **The test suite structurally cannot detect any of this.** Rendering without
   asserting proves only the absence of exceptions. Until numerical assertions
   exist, no fix below is protected against regression.

---

## Remaining work

In priority order, everything not closed above:

1. **M4 — render polygon holes.** The only remaining item that affects what a
   figure looks like. Needs a shared compound-`PathPatch` helper adopted by all
   four `_draw_patch*` functions, with interior rings carried through
   `_split_ring_at_cut`. Budget real time for the antimeridian cases.
2. **M1/M2 — custom tick label text and `xlabeldir`.** Features. Decide whether
   they are wanted at all before building them; if not, drop the parameters at
   the next breaking change rather than leaving them to warn forever.
3. **M8 — assertions in the example tests.** `tests/test_regressions.py` covers
   the reviewed defects, but the 29 example scripts still assert nothing. The
   cheapest strong safeguard is a pixel-baseline check: store the current
   `tests/outputs/*.png` as references and compare with a tolerance, exactly as
   was done to verify these fixes. That would have caught both regressions I
   introduced and backed out during this pass.
4. **L1** — `grid.py`'s `diag_offset_y` is implemented but never invoked with a
   non-zero value; either use it or drop it.
5. **L4** — stale `py_m_map.egg-info/SOURCES.txt` (8 of 27 modules). Harmless,
   since `packages.find` auto-discovers; regenerate on the next build.
6. **L6** — no `README`; `Py_M_Map.zip`, `.DS_Store` and `.pytest_cache/` sit in
   the tree. A `README` explaining the m_map correspondence would help students
   most.

### A note on method

Two of the fixes in this pass were wrong on the first attempt, and both were
caught only by rendering the example figures and comparing them to the previous
output — not by the test suite, which passed throughout. Specifically: forcing
contourf colourbars discrete broke `example16`'s banded-image bar, and resampling
the band colormap broke the case where contourf already supplies a band-indexed
map. Any future change to `colorbar.py`, `coast.py` or `projection.py` deserves
the same before/after image comparison. Item 3 above is how to make that
automatic.
