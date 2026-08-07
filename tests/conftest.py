"""
Shared pytest configuration, including the image-baseline check.

The example tests each render a figure and save it under ``tests/outputs/``.  On
their own they assert nothing, so a change that silently alters a map still
passes.  The autouse fixture below closes that gap without touching any of them:
after each test it finds the PNGs that test just wrote and compares them against
a stored reference in ``tests/baseline/``.

Regenerating the baseline
-------------------------
After an *intended* visual change, re-render and bless the new output::

    PY_M_MAP_UPDATE_BASELINE=1 pytest tests -q

Review the diff images first (see below) and commit the baseline change together
with the code change, so the reason for it is on the record.

Skipping the check entirely (e.g. on a machine with different fonts)::

    PY_M_MAP_SKIP_BASELINE=1 pytest tests -q

When a comparison fails, a three-panel ``<name>.png`` (baseline / current /
difference) is written to ``tests/outputs/_baseline_diffs/`` to make the change
easy to eyeball.  The check runs after the test body, so pytest reports it as an
*error at teardown* of that test rather than a plain failure; either way the run
fails and the message names the file and the tolerance.

Caveats
-------
Baselines are specific to the rendering stack that produced them — a different
matplotlib, freetype, or cartopy version will shift antialiasing and text metrics
and can trip the tolerances.  They guard against *code* regressions on one
machine; they are not a cross-platform conformance suite.  ``TOLERANCES`` below
records the per-example allowances and why each one exists.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
OUTPUT_DIR = _HERE / 'outputs'
BASELINE_DIR = _HERE / 'baseline'
DIFF_DIR = OUTPUT_DIR / '_baseline_diffs'

UPDATE = os.environ.get('PY_M_MAP_UPDATE_BASELINE', '') not in ('', '0')
SKIP = os.environ.get('PY_M_MAP_SKIP_BASELINE', '') not in ('', '0')

# Fraction of pixels allowed to differ by more than CHANNEL_EPS in any channel.
#
# Zero, deliberately.  matplotlib's Agg output is deterministic, so re-rendering
# on the same stack reproduces the previous PNG exactly — a tolerance would only
# buy cross-version slack, which these baselines do not promise anyway (see the
# caveats above), while hiding real changes.  For scale: fixing the Caspian Sea
# land mask moved 0.039 % of one figure's pixels, so any non-trivial allowance
# would have let that class of defect through unnoticed.  CHANNEL_EPS still
# absorbs last-bit float rounding.  Use TOLERANCES for genuinely unstable outputs.
DEFAULT_MAX_DIFF_FRACTION = 0.0
CHANNEL_EPS = 2.0 / 255.0

# Canvas size wobbles by a pixel with bbox_inches='tight' as text metrics shift;
# up to this much is compared on the overlapping region instead of failing.
SHAPE_SLACK_PX = 3

# Per-output overrides, each with the reason it is needed.
TOLERANCES: dict[str, float] = {
    # example9 fetches GSHHS at run time.  The upstream URL currently 404s and the
    # coastline is omitted (see the m_gshhs warning); if the download starts
    # working again the map legitimately changes and the baseline needs redoing.
    # Left strict deliberately, so that transition is noticed rather than absorbed.
}


def _gshhs_signature(gshhs_module) -> str:
    """
    Which GSHHS loads failed, as a stable one-line signature.

    Empty string when none did, so figures that use no GSHHS data compare normally.
    """
    if gshhs_module is None:
        return ''
    failures = sorted({f'{scale}:{level}'
                       for scale, level, _reason in gshhs_module.load_failures()})
    return ' '.join(failures)


def _signature_path(reference: Path) -> Path:
    """Sidecar recording the data state a reference was blessed under."""
    return reference.with_suffix('.gshhs.txt')


def _record_signature(reference: Path, signature: str) -> None:
    """Store the data state alongside a reference, or remove a stale sidecar."""
    target = _signature_path(reference)
    if signature:
        target.write_text(signature + '\n')
    elif target.exists():
        target.unlink()


def _read_signature(reference: Path) -> str:
    target = _signature_path(reference)
    return target.read_text().strip() if target.exists() else ''


def _png_state(directory: Path) -> dict[Path, tuple[float, int]]:
    """mtime and size of every PNG under `directory`, excluding diff output."""
    state: dict[Path, tuple[float, int]] = {}
    if not directory.is_dir():
        return state
    for path in directory.rglob('*.png'):
        if DIFF_DIR in path.parents or path.parent == DIFF_DIR:
            continue
        try:
            st = path.stat()
        except OSError:
            continue
        state[path] = (st.st_mtime, st.st_size)
    return state


def _load(path: Path):
    import matplotlib.pyplot as plt
    import numpy as np
    img = plt.imread(path)
    if img.ndim == 2:
        img = img[:, :, None]
    return np.asarray(img, dtype=float)


def _write_diff_panel(name: str, base, cur, diff) -> Path | None:
    """Three-panel baseline/current/difference image, for eyeballing a failure."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except Exception:
        return None
    DIFF_DIR.mkdir(parents=True, exist_ok=True)
    out = DIFF_DIR / f'{name}.png'
    fig, axs = plt.subplots(1, 3, figsize=(18, 6))
    for ax, img, title in (
        (axs[0], base, 'baseline'),
        (axs[1], cur, 'current'),
        (axs[2], diff, 'difference'),
    ):
        ax.imshow(img.squeeze(), cmap=None if img.shape[-1] >= 3 else 'gray')
        ax.set_title(f'{name} — {title}', fontsize=12)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.tight_layout()
    fig.savefig(out, dpi=90)
    plt.close(fig)
    return out


def _compare(current: Path, baseline: Path) -> str | None:
    """Return a failure message, or None when the images match within tolerance."""
    import numpy as np

    cur = _load(current)
    base = _load(baseline)

    if cur.shape != base.shape:
        dh = abs(cur.shape[0] - base.shape[0])
        dw = abs(cur.shape[1] - base.shape[1])
        if dh > SHAPE_SLACK_PX or dw > SHAPE_SLACK_PX or cur.shape[2] != base.shape[2]:
            return (f'canvas size changed from {base.shape[1]}x{base.shape[0]} to '
                    f'{cur.shape[1]}x{cur.shape[0]} px (beyond {SHAPE_SLACK_PX} px '
                    f'slack) — if intended, regenerate the baseline')
        h = min(cur.shape[0], base.shape[0])
        w = min(cur.shape[1], base.shape[1])
        cur, base = cur[:h, :w], base[:h, :w]

    delta = np.abs(cur - base).max(axis=2)
    frac = float((delta > CHANNEL_EPS).mean())
    limit = TOLERANCES.get(current.stem, DEFAULT_MAX_DIFF_FRACTION)
    if frac <= limit:
        return None

    panel = _write_diff_panel(current.stem, base, cur, delta)
    where = f'\n  diff image: {panel}' if panel else ''
    return (f'{frac * 100:.4f} % of pixels differ from the baseline '
            f'(limit {limit * 100:.4f} %, peak channel delta {delta.max():.3f}).'
            f'{where}\n'
            f'  baseline: {baseline}\n  current:  {current}\n'
            f'  If this change is intended, review the diff image then run:\n'
            f'    PY_M_MAP_UPDATE_BASELINE=1 pytest {current.stem and "tests"} -q')


@pytest.fixture(autouse=True)
def image_baseline(request):
    """
    Compare any PNG a test writes against ``tests/baseline/``.

    Tests that write no images (the unit/regression tests) are unaffected.
    """
    if SKIP:
        yield
        return

    # A GSHHS load failure only warns and omits the coastline, so a figure rendered
    # without that data is not comparable to a reference rendered with it — the
    # difference is data availability, not a code change (REVIEW.md M16).
    #
    # Comparing only when the data state *matches the reference* is what keeps this
    # useful. Skipping whenever any load fails would be too blunt: example9 requests
    # five GSHHS scales and one level 404s even on a primed cache, so that figure
    # would lose its guard permanently. Instead each reference records the set of
    # failures present when it was blessed, and the comparison runs when the current
    # set is identical.
    try:
        from py_m_map import gshhs as _gshhs
    except Exception:
        _gshhs = None
    if _gshhs is not None:
        _gshhs.clear_load_failures()

    before = _png_state(OUTPUT_DIR)
    yield
    after = _png_state(OUTPUT_DIR)

    signature = _gshhs_signature(_gshhs)

    written = sorted(p for p, meta in after.items() if before.get(p) != meta)
    if not written:
        return

    BASELINE_DIR.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []

    for path in written:
        reference = BASELINE_DIR / path.relative_to(OUTPUT_DIR)
        if UPDATE:
            reference.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, reference)
            _record_signature(reference, signature)
            continue
        if not reference.exists():
            # A newly added example: adopt its first render so the next run has
            # something to compare against, and say so rather than passing mutely.
            reference.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, reference)
            _record_signature(reference, signature)
            print(f'\n[baseline] created reference for new output {path.name} — '
                  f'check it looks right, then commit tests/baseline/{path.name}')
            continue

        blessed = _read_signature(reference)
        if blessed != signature:
            print(f'\n[baseline] skipped {path.name}: the GSHHS data available now '
                  f'differs from when the reference was blessed, so the figures are '
                  f'not comparable.\n'
                  f'    reference rendered with failures: {blessed or "(none)"}\n'
                  f'    this run:                        {signature or "(none)"}')
            continue

        message = _compare(path, reference)
        if message:
            failures.append(f'{path.name}: {message}')

    if failures:
        pytest.fail(
            'rendered output differs from the stored baseline:\n\n'
            + '\n\n'.join(failures),
            pytrace=False,
        )
