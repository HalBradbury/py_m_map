"""
m_windrose — wind roses at geographic locations on a map.

Port of MATLAB m_map/m_windrose.m (Pawlowicz, UBC EOAS).

Bars are fan-shaped patches drawn in projected map space so that
their angular width is proportional to their radius, matching the
MATLAB appearance on oblique and other non-conformal projections.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.collections as mcollections
import matplotlib.patches as mpatches
from .projection import m_ll2xy
from ._state import get_state


_DEFAULT_NSPEEDS = np.array([0, 4, 8, 12, 16, 20], dtype=float)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _ensure_list_of_arrays(x):
    """Convert x to a list of 1-D float arrays."""
    if isinstance(x, np.ndarray):
        if x.ndim <= 1:
            return [x.ravel().astype(float)]
        return [x[i].astype(float) for i in range(len(x))]
    if isinstance(x, (list, tuple)) and len(x) > 0:
        first = x[0]
        if isinstance(first, (list, tuple, np.ndarray)) and np.ndim(first) >= 1:
            return [np.asarray(xi, float).ravel() for xi in x]
        return [np.asarray(x, float).ravel()]
    return [np.asarray(x, float).ravel()]


def _local_deform(lon0: float, lat0: float):
    """
    Finite-difference local east/north unit vectors in map coordinates.

    Returns
    -------
    dXE, dYE : change in projected (x, y) per 0.001° eastward movement
    dXN, dYN : change in projected (x, y) per 0.001° northward movement
    (All scaled so that 1 unit = change from 0.001° displacement.)
    """
    cos_lat = max(abs(np.cos(np.radians(lat0))), 1e-6)
    pts_lon = np.array([lon0, lon0, lon0 + 0.001 / cos_lat])
    pts_lat = np.array([lat0, lat0 + 0.001, lat0])
    X, Y = m_ll2xy(pts_lon, pts_lat, clip='off')
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    # Index 0 = origin, 1 = north-displaced, 2 = east-displaced
    dXN = (X[1] - X[0]) * 1000
    dYN = (Y[1] - Y[0]) * 1000
    dXE = (X[2] - X[0]) * 1000
    dYE = (Y[2] - Y[0]) * 1000
    return dXE, dYE, dXN, dYN


def _sc(dirs_rad, dXE, dYE, dXN, dYN):
    """
    Map geographic direction angles to complex map-space offsets.

    dirs_rad : angle(s) measured clockwise from north (standard meteorological
               bearing), in radians.
    Returns complex array: real part = Δx in map space, imag = Δy.
    """
    sin_d = np.sin(dirs_rad)   # eastward component
    cos_d = np.cos(dirs_rad)   # northward component
    return (sin_d * dXE + cos_d * dXN) + 1j * (sin_d * dYE + cos_d * dYN)


def _bin_wind(thet, spd, nspds, ndirs):
    """
    Bin wind observations into a direction × speed histogram.

    Parameters
    ----------
    thet : 1-D array of wind directions in degrees (FROM which wind blows).
    spd  : 1-D array of wind speeds (same units as nspds).
    nspds : speed bin edges (length Ns+1).
    ndirs : number of direction bins.

    Returns
    -------
    N_cum : (ndirs, Ns+1) float array
        N_cum[d, 0] = 0 always.
        N_cum[d, s+1] = cumulative frequency (%) through speed bin s
        for direction bin d.
    """
    thet = np.asarray(thet, float).ravel()
    spd  = np.asarray(spd,  float).ravel()
    valid = np.isfinite(thet) & np.isfinite(spd) & (spd >= 0)
    thet, spd = thet[valid], spd[valid]
    ntot = len(thet)
    Ns = len(nspds) - 1

    if ntot == 0:
        return np.zeros((ndirs, Ns + 1), dtype=float)

    ang = 360.0 / ndirs
    # Shift by half a bin so bin 0 is centred at 0° (north)
    dir_idx = np.floor((thet % 360 + ang / 2) / ang).astype(int) % ndirs
    # Speed bins: obs in [nspds[s], nspds[s+1]) go to bin s
    spd_idx = np.clip(np.searchsorted(nspds[1:], spd, side='right'), 0, Ns - 1)

    N = np.zeros((ndirs, Ns), dtype=int)
    np.add.at(N, (dir_idx, spd_idx), 1)

    N_cum = np.zeros((ndirs, Ns + 1), dtype=float)
    N_cum[:, 1:] = np.cumsum(N, axis=1) / ntot * 100.0
    return N_cum


# ─── drawing helpers ───────────────────────────────────────────────────────────

def _draw_background(x0, y0, sc_bg, maxrad, nrings_vals, nrings_max,
                     labelrings, ax, dXE, dYE, dXN, dYN):
    """White-filled background circle, percentage rings, and radial spokes."""
    bg_pts = np.column_stack([x0 + sc_bg.real, y0 + sc_bg.imag])

    # White filled circle
    bg_patch = mpatches.Polygon(
        bg_pts, closed=True,
        facecolor='white', edgecolor='k', linewidth=0.4, zorder=2,
    )
    ax.add_patch(bg_patch)

    # Percentage rings
    for r_pct in nrings_vals:
        r_frac = r_pct / nrings_max
        ax.plot(
            x0 + sc_bg.real * r_frac,
            y0 + sc_bg.imag * r_frac,
            '-', color='0.7', linewidth=0.3, zorder=3,
        )
        if labelrings:
            # Label just outside the topmost point of this ring
            top_i = np.argmax(sc_bg.imag * r_frac)
            ax.text(
                x0 + sc_bg.real[top_i] * r_frac * 1.08,
                y0 + sc_bg.imag[top_i] * r_frac * 1.08,
                f'{r_pct:.0f}%',
                fontsize=5, ha='center', va='bottom', zorder=5,
            )

    # Radial spokes (4 diameters: N-S, NE-SW, E-W, SE-NW)
    for spoke_deg in np.arange(0, 180, 45):
        sc_p = _sc(np.radians(spoke_deg),       dXE, dYE, dXN, dYN)
        sc_m = _sc(np.radians(spoke_deg + 180), dXE, dYE, dXN, dYN)
        abs_p, abs_m = abs(sc_p), abs(sc_m)
        if abs_p > 1e-12 and abs_m > 1e-12:
            ax.plot(
                [x0 + sc_p.real / abs_p * maxrad,
                 x0 + sc_m.real / abs_m * maxrad],
                [y0 + sc_p.imag / abs_p * maxrad,
                 y0 + sc_m.imag / abs_m * maxrad],
                '-', color='0.7', linewidth=0.3, zorder=3,
            )


def _make_bars(x0, y0, N_cum, nspds, ndirs, sc_dir, nrings_max, alpha, kwargs):
    """
    Build and add a PolyCollection of frequency bars for one rose.

    Each bar is a fan-shaped quadrilateral (4 vertices) whose radial extent
    maps cumulative frequency to distance from the rose centre.
    """
    Ns = len(nspds) - 1
    ang_deg = 360.0 / ndirs
    # Angular half-width factor: at radius r, the bar spans ±r*yfac laterally
    yfac = np.tan(np.radians(ang_deg / 2)) * 0.9

    # Pre-scale: multiply by sc_dir/nrings_max so that a frequency of
    # nrings_max maps to a distance of maxrad from the centre.
    sc_scaled = sc_dir / nrings_max

    all_verts  = []
    all_colors = []

    for s in range(Ns):
        for d in range(ndirs):
            r1 = N_cum[d, s]
            r2 = N_cum[d, s + 1]
            if r2 <= r1:
                continue
            sc = sc_scaled[d]
            # Fan-shape: four corners in the local radial frame, then rotated/
            # scaled into map space by multiplying by the complex direction unit.
            z = np.array([
                complex(r1, -r1 * yfac),   # inner trailing edge
                complex(r2, -r2 * yfac),   # outer trailing edge
                complex(r2,  r2 * yfac),   # outer leading edge
                complex(r1,  r1 * yfac),   # inner leading edge
            ]) * sc
            all_verts.append(np.column_stack([x0 + z.real, y0 + z.imag]))
            all_colors.append((nspds[s] + nspds[s + 1]) / 2.0)

    if not all_verts:
        return None

    kw = dict(kwargs)
    if 'edgecolor' not in kw and 'edgecolors' not in kw:
        kw['edgecolors'] = 'none'

    ax = plt.gca()
    pc = mcollections.PolyCollection(
        all_verts,
        array=np.array(all_colors, dtype=float),
        alpha=alpha,
        zorder=4,
        **kw,
    )
    ax.add_collection(pc)
    return pc


# ─── public API ────────────────────────────────────────────────────────────────

def m_windrose(lon, lat, thet, spd, *,
               nspeeds=None,
               ndirs=16,
               size=0.075,
               nrings=None,
               labelrings=False,
               alpha=0.4,
               parts='all',
               **kwargs):
    """
    Draw wind roses at one or more geographic locations on the current map.

    Parameters
    ----------
    lon, lat : scalar or sequence of scalars
        Geographic position(s) in decimal degrees.
    thet : array-like or list of array-like
        Wind direction(s) in degrees (FROM which wind blows; 0°=N, 90°=E).
        Pass a list of arrays for multi-station input.
    spd : array-like or list of array-like
        Wind speed(s) in the same units as ``nspeeds``.
    nspeeds : array-like, optional
        Speed bin edges.  Default ``[0, 4, 8, 12, 16, 20]``.
    ndirs : int
        Number of direction bins.  Default 16.
    size : float
        Rose radius as fraction of the smaller map dimension.  Default 0.075.
    nrings : array-like, optional
        Percentage values at which to draw ring lines.  If None, three evenly
        spaced rings are computed from the data.
    labelrings : bool
        Label the percentage rings (default False).
    alpha : float
        Bar transparency (0=transparent, 1=opaque).  Default 0.4.
    parts : {'all', 'background', 'bar'}
        Which elements to draw.  'all' (default) performs a two-pass layout
        so all rose backgrounds are drawn before any bars, preventing nearby
        roses from obscuring each other's bars.
    **kwargs
        Forwarded to :class:`~matplotlib.collections.PolyCollection`
        (e.g. ``edgecolors='k'``, ``linewidths=0.5``).

    Returns
    -------
    pcs : list of :class:`~matplotlib.collections.PolyCollection` or None
        One PolyCollection per station (``None`` for out-of-bounds or empty
        stations).  The last non-None entry is registered as the current
        image via ``plt.sci()`` so that subsequent ``plt.clim()`` /
        ``plt.colormap()`` calls affect all collections in the axes.
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    nspds = np.asarray(
        nspeeds if nspeeds is not None else _DEFAULT_NSPEEDS, dtype=float
    )

    lons  = np.atleast_1d(np.asarray(lon, float)).ravel()
    lats  = np.atleast_1d(np.asarray(lat, float)).ravel()
    thets = _ensure_list_of_arrays(thet)
    spds  = _ensure_list_of_arrays(spd)

    nstations = len(lons)

    if len(thets) != nstations:
        if len(thets) == 1:
            thets = thets * nstations
        else:
            raise ValueError(
                f"lon has {nstations} entries but thet has {len(thets)}"
            )
    if len(spds) != nstations:
        if len(spds) == 1:
            spds = spds * nstations
        else:
            raise ValueError(
                f"lon has {nstations} entries but spd has {len(spds)}"
            )

    x_range = state.x_limits[1] - state.x_limits[0]
    y_range = state.y_limits[1] - state.y_limits[0]
    maxrad = size * min(x_range, y_range) / 2.0

    # ── pre-compute per-station geometry and histograms ──────────────────────
    stations = []
    for k in range(nstations):
        lon_k = float(lons[k])
        lat_k = float(lats[k])

        X_k, Y_k = m_ll2xy(
            np.array([lon_k]), np.array([lat_k]), clip='on'
        )
        x0 = float(np.asarray(X_k, float).ravel()[0])
        y0 = float(np.asarray(Y_k, float).ravel()[0])
        if not (np.isfinite(x0) and np.isfinite(y0)):
            stations.append(None)
            continue

        dXE, dYE, dXN, dYN = _local_deform(lon_k, lat_k)

        # Deformed background circle (73 points → 72 arcs → closed polygon)
        ang_circ = np.linspace(0, 2 * np.pi, 73)
        sc_bg_raw = _sc(ang_circ, dXE, dYE, dXN, dYN)
        bg_scale  = np.max(np.abs(sc_bg_raw))
        sc_bg = sc_bg_raw / bg_scale * maxrad if bg_scale > 0 else sc_bg_raw

        # Direction-bin unit vectors (one per bin, pointing in bin's centre)
        ang_deg   = 360.0 / ndirs
        cdirs_rad = np.radians(np.arange(ndirs) * ang_deg)
        sc_dir_raw = _sc(cdirs_rad, dXE, dYE, dXN, dYN)
        dir_scale  = np.max(np.abs(sc_dir_raw))
        sc_dir = sc_dir_raw / dir_scale * maxrad if dir_scale > 0 else sc_dir_raw

        N_cum = _bin_wind(thets[k], spds[k], nspds, ndirs)

        if nrings is not None:
            nrings_vals = np.asarray(nrings, float)
            nrings_max_k = float(nrings_vals[-1])
        else:
            nrmax = float(np.max(N_cum[:, -1]))
            nrmax = max(nrmax, 1.0)
            nrings_max_k = nrmax
            nrings_vals = np.round(np.linspace(nrmax / 3, nrmax, 3), 1)

        stations.append({
            'x0': x0, 'y0': y0,
            'dXE': dXE, 'dYE': dYE, 'dXN': dXN, 'dYN': dYN,
            'sc_bg': sc_bg, 'sc_dir': sc_dir,
            'N_cum': N_cum,
            'nrings_vals': nrings_vals,
            'nrings_max': nrings_max_k,
        })

    # ── two-pass drawing ─────────────────────────────────────────────────────
    ax = plt.gca()
    pcs = [None] * nstations

    draw_bg  = parts in ('all', 'background')
    draw_bar = parts in ('all', 'bar')

    if draw_bg:
        for k, st in enumerate(stations):
            if st is None:
                continue
            _draw_background(
                st['x0'], st['y0'], st['sc_bg'], maxrad,
                st['nrings_vals'], st['nrings_max'],
                labelrings, ax,
                st['dXE'], st['dYE'], st['dXN'], st['dYN'],
            )

    if draw_bar:
        for k, st in enumerate(stations):
            if st is None:
                continue
            pc = _make_bars(
                st['x0'], st['y0'], st['N_cum'], nspds, ndirs,
                st['sc_dir'], st['nrings_max'], alpha, dict(kwargs),
            )
            pcs[k] = pc

    # Register the last non-None collection as the current image so that
    # plt.clim() / plt.colormap() affect it.
    for pc in reversed(pcs):
        if pc is not None:
            plt.sci(pc)
            break

    return pcs
