"""
Numerical regression tests — the assertions the example scripts do not make.

The 29 test_example*.py / test_sat_ex*.py files render a figure and check only
that nothing raised.  That cannot catch a wrong coordinate, a mislabelled land
point, or a colourbar that misrepresents its plot.  Every test here pins down a
specific defect fixed after the 2026-08-05 review (see REVIEW.md) so it cannot
come back silently.

Run just these:

    pytest tests/test_regressions.py -v
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import py_m_map as mm
from py_m_map._state import get_state


@pytest.fixture(autouse=True)
def _clean_state():
    """Every test starts from a clean projection state and closes its figures."""
    mm.reset_state()
    yield
    plt.close('all')
    mm.reset_state()


# ---------------------------------------------------------------------------
# Projection setup and coordinate transforms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('projection', ['lambert', 'albers'])
@pytest.mark.parametrize('lat', [[-60, 60], [-45, 45], [-10, 10], [40, 55]])
def test_conic_accepts_equator_symmetric_ranges(projection, lat):
    """
    H4: standard parallels were mean ± span/6, summing to zero for any range
    symmetric about the equator, which Proj rejects outright.
    """
    mm.m_proj(projection, lon=[-180, 180], lat=lat)
    lon_c, lat_c = 0.0, float(np.mean(lat))
    x, y = mm.m_ll2xy(lon_c, lat_c, clip='off')
    lon_r, lat_r = mm.m_xy2ll(x, y)
    assert float(lon_r) == pytest.approx(lon_c, abs=1e-6)
    assert float(lat_r) == pytest.approx(lat_c, abs=1e-6)


def test_oblique_inverse_round_trips():
    """
    H6/H7: m_xy2ll raised TypeError for oblique projections because a bare
    forward closure was stored in state.proj.  Once callable, the inverse also
    had to actually invert — a quadrant-folding arctan in the forward made it
    return the antipode.
    """
    mm.m_proj('oblique', lon=[-130, -120], lat=[45, 50])
    for lon, lat in [(-130, 45), (-120, 50), (-125, 47.5), (-128, 46)]:
        x, y = mm.m_ll2xy(lon, lat, clip='off')
        lon_r, lat_r = mm.m_xy2ll(x, y)
        assert float(lon_r) == pytest.approx(lon, abs=1e-6), f'lon at {(lon, lat)}'
        assert float(lat_r) == pytest.approx(lat, abs=1e-6), f'lat at {(lon, lat)}'


def test_x_offset_does_not_leak_between_projections():
    """
    H5: the pseudocylindrical lobe offset was never cleared, so it was added to
    every transform of whatever projection came next.
    """
    mm.m_proj('mollweide', lon=[0, 180], lat=[-90, 90])
    assert abs(get_state().x_offset) > 1e5, 'expected an off-centre lobe to set an offset'

    mm.m_proj('mercator', lon=[-180, 180], lat=[-80, 80])
    assert get_state().x_offset == 0.0

    x, y = mm.m_ll2xy(np.array([0.0]), np.array([0.0]))
    assert float(x[0]) == pytest.approx(0.0, abs=1.0)


def test_center_lat_lon_do_not_leak_between_projections():
    """M3: same root cause as H5, via the circular-projection centre."""
    mm.m_proj('stereographic', lat=90, lon=0, radius=30)
    assert get_state().center_lat == pytest.approx(90.0)

    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    assert get_state().center_lat == 0.0
    assert get_state().center_lon == 0.0


def test_m_ll2xy_accepts_scalars_under_a_lobed_projection():
    """
    H7: adding the lobe offset demoted a 0-d array to a numpy scalar, so the
    clip step's item assignment raised TypeError — for in-range points too.
    """
    mm.m_proj('mollweide', lon=[0, 180], lat=[-90, 90])
    x, y = mm.m_ll2xy(90.0, 0.0)                      # in range
    assert np.isfinite(np.asarray(x)).all()
    x_out, y_out = mm.m_ll2xy(-90.0, 0.0)             # out of range
    assert np.isnan(np.asarray(x_out)).all()


def test_m_ll2xy_scalar_clipping_on_plain_projection():
    """Scalar in/out-of-range handling must keep working without an offset."""
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    x_in, _ = mm.m_ll2xy(-120.0, 45.0)
    assert np.isfinite(np.asarray(x_in)).all()
    x_out, _ = mm.m_ll2xy(10.0, 45.0)
    assert np.isnan(np.asarray(x_out)).all()


@pytest.mark.parametrize('spelling', [
    'azimuthal equal-area', 'azimuthal equal area', 'azimuthal_equal_area',
])
def test_azimuthal_equal_area_spellings(spelling):
    """M5: the underscore form fell through to a non-existent projection."""
    mm.m_proj(spelling, lon=0, lat=0)
    assert get_state().projection_name == 'azimuthal_equal_area'


def test_oblique_at_equator_has_no_divide_by_zero():
    """M6: tan(lat) is zero for a limit on the equator."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        mm.m_proj('oblique', lon=[0, 10], lat=[0, 10])
    assert not [w for w in caught if 'divide by zero' in str(w.message)]


def test_m_proj_required_before_transforms():
    """The error a student sees when calling things in the wrong order."""
    with pytest.raises(RuntimeError, match='m_proj'):
        mm.m_ll2xy(0.0, 0.0)


# ---------------------------------------------------------------------------
# Land masking
# ---------------------------------------------------------------------------

def test_landmask_excludes_enclosed_water():
    """
    H1: polygon interior rings were ignored, so lakes and inland seas came back
    as land.  The Caspian is the largest instance in the 110 m dataset.
    """
    mm.m_proj('equidistant', lon=[30, 70], lat=[30, 55])
    lon = np.array([52.0, 65.0])          # Caspian centre, then Kazakh steppe
    lat = np.array([41.0, 45.0])
    mask = np.asarray(mm.m_landmask(lon, lat)).ravel()
    assert mask[0] == False, 'Caspian Sea must not be land'   # noqa: E712
    assert mask[1] == True, 'Central Asian land must be land'  # noqa: E712


def test_landmask_basic_land_and_ocean():
    """Guard the ordinary cases while fixing the holes."""
    mm.m_proj('equidistant', lon=[-60, 40], lat=[-10, 60])
    lon = np.array([-30.0, 2.3, 10.0])     # mid-Atlantic, Paris, Sahara
    lat = np.array([30.0, 48.9, 25.0])
    mask = np.asarray(mm.m_landmask(lon, lat)).ravel()
    assert list(mask) == [False, True, True]


# ---------------------------------------------------------------------------
# Elevation data
# ---------------------------------------------------------------------------

def _etopo1_available() -> bool:
    from py_m_map import etopo
    return etopo._etopo1_path() is not None


@pytest.mark.skipif(not _etopo1_available(), reason='ETOPO1 binary not installed')
def test_etopo1_antimeridian_region():
    """
    H2: the straddle test ran after the modulo wrap, so it could never fire and
    the contiguous branch was handed a negative width.
    """
    from py_m_map import etopo
    lons, lats, Z = etopo._read_etopo1_region(170, 190, 40, 50)
    assert Z.shape == (len(lats), len(lons))
    assert lons[0] < 170.0 and lons[-1] > 189.0
    assert np.all(np.diff(lons) > 0), 'longitudes must stay ascending across the join'
    # North Pacific: deep trench floor up to near sea level, nothing absurd.
    assert -12000 < np.nanmin(Z) < -3000
    assert np.nanmax(Z) < 5000


@pytest.mark.skipif(not _etopo1_available(), reason='ETOPO1 binary not installed')
def test_etopo1_contiguous_region_unchanged():
    """The ordinary path must be unaffected by the straddle fix."""
    from py_m_map import etopo
    lons, lats, Z = etopo._read_etopo1_region(-130, -110, 40, 50)
    assert Z.shape == (len(lats), len(lons))
    assert np.all(np.diff(lons) > 0)
    assert np.nanmin(Z) < 0 < np.nanmax(Z), 'NE Pacific margin spans coastline'


# ---------------------------------------------------------------------------
# Colourbar
# ---------------------------------------------------------------------------

def _grid_data():
    lon = np.linspace(-130, -110, 40)
    lat = np.linspace(40, 55, 30)
    LO, LA = np.meshgrid(lon, lat)
    return LO, LA, np.hypot(LO + 120, LA - 47)


def test_contfbar_is_discrete_for_contourf():
    """
    H3: the discrete/continuous choice was made from the colormap's resolution
    alone, so a contourf drawn with a smooth 256-colour map got a gradient bar
    that did not match its bands.
    """
    from matplotlib.colors import BoundaryNorm
    LO, LA, D = _grid_data()
    levels = [0, 2, 4, 6, 8, 10]

    fig, ax = plt.subplots(figsize=(5, 4))
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    mm.m_contourf(LO, LA, D, levels=levels, cmap='viridis')
    _, cb = mm.m_contfbar([0.1, 0.9], 0.05, D, levels)
    assert isinstance(cb.norm, BoundaryNorm)
    # The bands must span the colormap rather than all coming from one end of a
    # continuous lut — the failure mode when BoundaryNorm's integer indices are
    # used against a 128- or 256-entry map.
    n_bands = len(levels) - 1
    band_rgb = np.array([cb.cmap(i)[:3] for i in range(n_bands)])
    assert np.ptp(band_rgb) > 0.3, f'band colours collapsed: {band_rgb.tolist()}'
    assert len({tuple(np.round(c, 4)) for c in band_rgb}) == n_bands, \
        'each band must get a distinct colour'


def test_contfbar_ignores_the_contour_line_overlay():
    """
    m_contourf draws black contour lines on top of its filled bands, so the most
    recent artist is that unfilled overlay.  Taking the colormap from it gave an
    all-black colourbar for anyone relying on the default colormap=None.
    """
    LO, LA, D = _grid_data()
    levels = [0, 2, 4, 6, 8, 10]

    fig, ax = plt.subplots(figsize=(5, 4))
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    mm.m_contourf(LO, LA, D, levels=levels, cmap='viridis')
    _, cb = mm.m_contfbar([0.1, 0.9], 0.05, D, levels)

    band_rgb = np.array([cb.cmap(i)[:3] for i in range(len(levels) - 1)])
    assert np.ptp(band_rgb) > 0.3, (
        f'colourbar took its colours from the black line overlay: '
        f'{band_rgb.tolist()}'
    )


def test_contfbar_is_continuous_for_an_image():
    """
    The counterpart: an image with a smooth colormap is a gradient, and forcing
    bands on it would invent structure the figure does not have.
    """
    from matplotlib.colors import Normalize
    LO, LA, D = _grid_data()

    fig, ax = plt.subplots(figsize=(5, 4))
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    ax.imshow(D, cmap='viridis', extent=[-1e6, 1e6, 5e6, 7e6])
    _, cb = mm.m_contfbar([0.1, 0.9], 0.05, D, [0, 2, 4, 6, 8, 10])
    assert isinstance(cb.norm, Normalize)
    assert not hasattr(cb.norm, 'boundaries')


def test_contfbar_discrete_override():
    """The inference can be overridden when the bar is not for the last artist."""
    from matplotlib.colors import BoundaryNorm, Normalize
    LO, LA, D = _grid_data()

    fig, ax = plt.subplots(figsize=(5, 4))
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    ax.imshow(D, cmap='viridis', extent=[-1e6, 1e6, 5e6, 7e6])
    _, cb = mm.m_contfbar([0.1, 0.9], 0.05, D, [0, 2, 4, 6, 8, 10], discrete=True)
    assert isinstance(cb.norm, BoundaryNorm)


# ---------------------------------------------------------------------------
# m_grid parameter honesty
# ---------------------------------------------------------------------------

def test_custom_ticklabels_warn_instead_of_being_ignored():
    """M1: label text was silently discarded."""
    fig, ax = plt.subplots(figsize=(5, 4))
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    with pytest.warns(UserWarning, match='xticklabels'):
        mm.m_grid(xtick=[-125, -120, -115], xticklabels=['West', 'Mid', 'East'])


def test_xlabeldir_warns_instead_of_being_ignored():
    """M2: the parameter was accepted and never read."""
    fig, ax = plt.subplots(figsize=(5, 4))
    mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
    with pytest.warns(UserWarning, match='xlabeldir'):
        mm.m_grid(xlabeldir='end')


def test_supported_ticklabel_forms_do_not_warn():
    """None / False / [] are the documented on-off forms and must stay quiet."""
    for value in (None, False, []):
        mm.reset_state()
        fig, ax = plt.subplots(figsize=(5, 4))
        mm.m_proj('mercator', lon=[-130, -110], lat=[40, 55])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            mm.m_grid(xticklabels=value, yticklabels=value)
        offenders = [str(w.message) for w in caught
                     if 'xticklabels' in str(w.message) or 'yticklabels' in str(w.message)]
        assert not offenders, f'{value!r} warned: {offenders}'
        plt.close(fig)


# ---------------------------------------------------------------------------
# m_pcolor clipping
# ---------------------------------------------------------------------------

def _global_grid():
    lon = np.arange(-179.5, 180.0, 1.0)
    lat = np.arange(-89.5, 90.0, 1.0)
    LO, LA = np.meshgrid(lon, lat)
    return LO, LA, np.cos(np.deg2rad(LA)) * 20.0


def test_m_pcolor_offmap_cells_do_not_take_the_bad_colour():
    """
    M9: off-map cells were only set to NaN, so they went through the colormap's
    "bad" colour — the same channel the caller's missing data uses.  With an opaque
    set_bad, a call whose data lies entirely off the map painted over the figure.

    This is the sat_ex1 failure: a Hammer centred at 150°W, the field drawn once
    correctly and once shifted by -360° (m_map's own idiom), with a white bad
    colour.  The second, fully out-of-range copy wiped out the first.
    """
    LO, LA, field = _global_grid()

    fig, ax = plt.subplots(figsize=(6, 4))
    mm.m_proj('hammer-aitoff', lon=-150.0, lat=[-90, 90])

    cmap = plt.get_cmap('viridis').copy()
    cmap.set_bad('white')

    mm.m_pcolor(LO, LA, field, cmap=cmap, vmin=0, vmax=20)
    second = mm.m_pcolor(LO - 360.0, LA, field, cmap=cmap, vmin=0, vmax=20)

    # Every cell of the second mesh is off-map, so all of it must be transparent.
    alpha = second.get_alpha()
    assert alpha is not None, 'expected a per-cell alpha array for an off-map mesh'
    assert np.asarray(alpha).max() == 0.0, (
        'a fully off-map m_pcolor is still opaque, so it paints over the map'
    )


def test_m_pcolor_keeps_caller_nans_visible_as_bad():
    """The complement: the caller's own missing data must still honour set_bad."""
    LO, LA, field = _global_grid()
    field = field.copy()
    field[40:50, 40:50] = np.nan          # a genuine hole, well inside the map

    fig, ax = plt.subplots(figsize=(6, 4))
    mm.m_proj('equidistant', lon=[-180, 180], lat=[-89, 89])
    cmap = plt.get_cmap('viridis').copy()
    cmap.set_bad('red')
    mesh = mm.m_pcolor(LO, LA, field, cmap=cmap, vmin=0, vmax=20)

    alpha = mesh.get_alpha()
    if alpha is not None:
        # Where the caller's data is NaN but the cell is on the map, it must stay
        # opaque so the bad colour shows.
        a = np.asarray(alpha)
        assert a[45, 45] == 1.0, 'a genuine NaN inside the map was hidden'
    # matplotlib converts NaN to a masked element, and masked is what routes a
    # cell to the colormap's "bad" colour — so that is what must be preserved.
    assert np.ma.getmaskarray(mesh.get_array())[45, 45], (
        'the caller NaN hole was not preserved, so set_bad will not show'
    )


def test_m_pcolor_untouched_when_nothing_is_clipped():
    """
    A fully on-map call must not gain an alpha array — otherwise every existing
    figure changes, and a caller's scalar alpha would be silently rewritten.
    """
    LO, LA, field = _global_grid()
    fig, ax = plt.subplots(figsize=(6, 4))
    mm.m_proj('equidistant', lon=[-180, 180], lat=[-89.5, 89.5])
    mesh = mm.m_pcolor(LO, LA, field)
    assert mesh.get_alpha() is None


def test_m_pcolor_scalar_alpha_is_preserved_for_visible_cells():
    """A caller's alpha must still apply where cells are on the map."""
    LO, LA, field = _global_grid()
    fig, ax = plt.subplots(figsize=(6, 4))
    mm.m_proj('hammer-aitoff', lon=-150.0, lat=[-90, 90])
    mesh = mm.m_pcolor(LO, LA, field, alpha=0.5)
    alpha = mesh.get_alpha()
    if alpha is None:
        assert True                       # nothing clipped; scalar passed through
    else:
        a = np.asarray(alpha)
        assert set(np.unique(a)) <= {0.0, 0.5}, f'unexpected alphas: {np.unique(a)}'
        assert (a == 0.5).any(), 'the visible cells lost the requested alpha'


# ---------------------------------------------------------------------------
# Circular grid labels
# ---------------------------------------------------------------------------

@pytest.mark.parametrize('proj_kwargs', [
    dict(projection='azimuthal equal-area', lat=90, lon=0, radius=47),
    dict(projection='stereographic', lat=90, lon=0, radius=40),
    dict(projection='ortho', lat=48, lon=-123),
])
def test_circular_grid_labels_are_never_inverted(proj_kwargs):
    """
    M10: labels were rotated tangentially, which is forced to ±90° at the left
    and right extremes of the circle.  Normalising into (-90, 90] cannot make
    those agree, so the right-hand label read bottom-to-top and the left-hand
    one top-to-bottom — the latter looking upside-down (90°W rendered as M∘006).
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    mm.m_proj(**proj_kwargs)
    mm.m_grid()

    labels = [t for t in ax.texts if t.get_text()]
    assert labels, 'expected some tick labels'
    for text in labels:
        # Normalise to (-180, 180]; anything outside (-90, 90] reads upside-down.
        rot = text.get_rotation() % 360.0
        if rot > 180.0:
            rot -= 360.0
        assert -90.0 < rot <= 90.0, (
            f'label {text.get_text()!r} rotated {rot}°, which reads inverted'
        )


def test_circular_latitude_labels_clear_the_meridian_labels():
    """
    M11: latitude labels default to each parallel's left-most point, which on a
    polar map is exactly where the 90°W meridian's own label sits.  The two
    overlapped into an illegible blob.  lat_label_lon separates them; this pins
    down that the override actually moves them clear.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    mm.m_proj('azimuthal equal-area', lat=90, lon=0, radius=47)
    mm.m_grid(lat_label_lon=-75.0)

    positions = {t.get_text(): np.array(t.get_position()) for t in ax.texts
                 if t.get_text()}
    assert '90°W' in positions and '50°N' in positions, sorted(positions)

    separation = np.linalg.norm(positions['90°W'] - positions['50°N'])
    # Map radius is ~5.3e6 m here; anything under a few per cent of that overlaps.
    radius = abs(mm.get_state().x_limits[1])
    assert separation > 0.05 * radius, (
        f'latitude and longitude labels are {separation:.0f} m apart '
        f'({100 * separation / radius:.1f} % of the map radius) — they overlap'
    )


@pytest.mark.parametrize('proj_kwargs', [
    dict(projection='ortho', lat=48, lon=-123),
    dict(projection='azimuthal equal-area', lat=90, lon=0, radius=47),
    dict(projection='stereographic', lat=90, lon=0, radius=40),
    dict(projection='stereographic', lat=90, lon=0, radius=30),
])
def test_circular_grid_labels_never_overlap(proj_kwargs):
    """
    M11/M14: labels were drawn on top of one another in several ways — far-side
    meridians all landing on the visible pole, ±180° labelled twice, parallels
    snapped to a shared radius, and a boundary-reaching parallel colliding with
    the left-most meridian's label.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    mm.m_proj(**proj_kwargs)
    mm.m_grid()

    positions = {t.get_text(): np.array(t.get_position())
                 for t in ax.texts if t.get_text()}
    radius = abs(mm.get_state().x_limits[1])
    names = list(positions)
    collisions = [
        (a, b) for i, a in enumerate(names) for b in names[i + 1:]
        if float(np.hypot(*(positions[a] - positions[b]))) < 0.04 * radius
    ]
    assert not collisions, f'labels overlap: {collisions}'


def test_ortho_does_not_label_the_far_hemisphere():
    """
    M14: every meridian converges at the poles, so a meridian on the invisible
    hemisphere still shows a sliver when a pole is in view.  Its lowest visible
    point is that pole, well inside the boundary (r/R = 0.672 here) — the guard
    meant to reject such meridians used a 0.65 threshold and let them all through,
    stacking four labels on the pole.  ±180° was also labelled twice.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    mm.m_proj('ortho', lat=48, lon=-123)
    mm.m_grid()

    labels = [t.get_text() for t in ax.texts if t.get_text()]
    # Visible hemisphere is roughly 147°E .. 33°W; these are on the far side.
    for far in ('0°E', '30°E', '60°E', '90°E'):
        assert far not in labels, f'{far} is on the invisible hemisphere'
    # 180°W and 180°E are one meridian and must not both appear.
    assert not ('180°W' in labels and '180°E' in labels), labels
    assert len(labels) == len(set(labels)), f'duplicate labels: {labels}'
    # The near-side meridians must survive.
    for near in ('120°W', '150°W', '150°E'):
        assert near in labels, f'{near} should be labelled; got {labels}'


def test_circular_latitude_labels_do_not_collapse_onto_each_other():
    """
    Along an explicit meridian every parallel shares one ray, so snapping labels
    out to the boundary circle stacked them all at the same point — making
    lat_label_lon useless for more than one parallel.
    """
    fig, ax = plt.subplots(figsize=(6, 6))
    mm.m_proj('stereographic', lat=90, lon=0, radius=40)
    mm.m_grid(lat_label_lon=-75.0)

    radii = {t.get_text(): float(np.hypot(*t.get_position()))
             for t in ax.texts if t.get_text().endswith('N')}
    assert len(radii) >= 2, f'expected several latitude labels, got {radii}'
    # Distinct parallels must sit at distinct distances from the pole.
    assert len(set(round(r, -4) for r in radii.values())) == len(radii), (
        f'latitude labels collapsed onto the same radius: {radii}'
    )


@pytest.mark.parametrize('projection,lon', [
    # hammer and robinson take a centre longitude; mollweide and sinusoidal
    # require an explicit range (see L7).
    ('hammer', 170.0),
    ('robinson', 170.0),
    ('mollweide', [-10.0, 350.0]),
    ('sinusoidal', [-10.0, 350.0]),
])
def test_pseudocylindrical_longitude_labels_are_spread_out(projection, lon):
    """
    M13: longitude labels were placed where each meridian crosses lat_min, which
    on a whole-world pseudocylindrical map is the pole every meridian converges
    at — so they all stacked at x ~ 0.  Seen in example 11.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    mm.m_proj(projection, lon=lon, lat=[-90, 90])
    mm.m_grid(grid='off')

    xs = sorted(t.get_position()[0] for t in ax.texts
                if t.get_text().endswith(('E', 'W')))
    assert len(xs) >= 2, f'expected several longitude labels, got {xs}'

    x_span = abs(mm.get_state().x_limits[1] - mm.get_state().x_limits[0])
    gaps = np.diff(xs)
    assert gaps.min() > 0.02 * x_span, (
        f'longitude labels are stacked: closest pair {gaps.min():.3e} m apart, '
        f'which is {100 * gaps.min() / x_span:.2f} % of the map width'
    )


# ---------------------------------------------------------------------------
# Fancy box corners
# ---------------------------------------------------------------------------

class _CornerRecorder:
    """Collects the line segments _draw_ruler_corner emits, classified by shape."""

    def __init__(self):
        self.segments = []

    # --- minimal Axes surface ------------------------------------------------
    def fill(self, *a, **k):
        return [_CornerRecorder._Patch()]

    def plot(self, xs, ys, *a, **k):
        self.segments.append((tuple(np.atleast_1d(xs)), tuple(np.atleast_1d(ys))))

    def add_patch(self, *a, **k):
        pass

    class _Patch:
        def set_antialiased(self, *_a):
            pass

    # --- classification, for a corner at (0,0) with dx = dy = -1 -------------
    #   diagonal   inner corner to outer corner
    #   sep_h      vertical line delimiting the box from the horizontal strip
    #   sep_v      horizontal line delimiting it from the vertical strip
    #   stub_h     half-line along the horizontal strip's centre line
    #   stub_v     half-line along the vertical strip's centre line
    SHAPES = {
        ((0.0, -1.0), (0.0, -1.0)): 'diagonal',
        ((0.0, 0.0), (0.0, -1.0)): 'sep_h',
        ((0.0, -1.0), (0.0, 0.0)): 'sep_v',
        ((0.0, -0.5), (-0.5, -0.5)): 'stub_h',
        ((-0.5, -0.5), (0.0, -0.5)): 'stub_v',
    }

    def kinds(self):
        out = []
        for xs, ys in self.segments:
            out.append(self.SHAPES.get((xs, ys), f'UNKNOWN{xs}{ys}'))
        return sorted(out)


@pytest.mark.parametrize('c_h,c_v,tick_h,tick_v,expected', [
    # A tick at the corner delimits it: the corner triangle becomes a new box
    # continuing the alternation, so it carries a line only when the strip beside
    # it is EMPTY.
    ('k', 'k', True, True, ['diagonal', 'sep_h', 'sep_v']),
    ('k', 'white', True, True, ['diagonal', 'sep_h', 'sep_v', 'stub_v']),
    ('white', 'k', True, True, ['diagonal', 'sep_h', 'sep_v', 'stub_h']),
    ('white', 'white', True, True,
     ['diagonal', 'sep_h', 'sep_v', 'stub_h', 'stub_v']),
    # No tick: nothing delimits the corner and the strip's own style runs on into
    # it as far as the diagonal, so the line is drawn when that strip is FULL.
    # The condition inverts — this is what sat_ex5 got wrong.
    ('k', 'k', False, False, ['diagonal', 'stub_h', 'stub_v']),
    ('k', 'white', False, False, ['diagonal', 'stub_h']),
    ('white', 'k', False, False, ['diagonal', 'stub_v']),
    ('white', 'white', False, False, ['diagonal']),
    # Mixed, as at sat_ex5's top-left (x-tick present, y-tick absent).
    ('k', 'k', True, False, ['diagonal', 'sep_h', 'stub_v']),
    ('white', 'white', False, True, ['diagonal', 'sep_v', 'stub_v']),
])
def test_ruler_box_corner_follows_the_tick_rule(c_h, c_v, tick_h, tick_v, expected):
    """
    The 'line' fancy box corner depends on whether a tick lands on it:

      tick present -> the corner is delimited by a separator, and begins a fresh
                      box, so it gets a line only when the neighbouring strip is
                      empty;
      no tick      -> nothing delimits it and the neighbour's style continues to
                      the diagonal, so it gets a line only when that strip is full.

    Previously the "empty" condition was used unconditionally, which is right only
    where ticks happen to land on both edges — the bottom-left corner of sat_ex5,
    and nowhere else on that frame.
    """
    from py_m_map import grid as gridmod

    rec = _CornerRecorder()
    gridmod._draw_ruler_corner(rec, 0.0, 0.0, -1.0, -1.0, c_h, c_v, lw=0.4,
                               tick_at_h=tick_h, tick_at_v=tick_v)
    assert rec.kinds() == sorted(expected), (
        f'c_h={c_h} c_v={c_v} tick_h={tick_h} tick_v={tick_v}: '
        f'got {rec.kinds()}, expected {sorted(expected)}'
    )
