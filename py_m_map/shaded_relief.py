"""
Shaded relief topography.

m_shadedrelief(lon, lat, Z) — ported from m_shadedrelief.m
"""
from __future__ import annotations
import warnings
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from .projection import m_ll2xy, m_xy2ll
from ._state import get_state


def _shade_rgb(ZI, dZdx, dZdy, cmap_rgb, light_angle, gradient, clip_val,
               nan_color, lake_color, caxis):
    """Convert ZI + gradient arrays to a shaded uint8 RGB image."""
    if caxis is None:
        caxis = (np.nanmin(ZI), np.nanmax(ZI))

    light_rad = np.radians(light_angle)
    Fnw = np.degrees(np.arctan(
        np.imag(-(dZdx + 1j * dZdy) * np.exp(1j * light_rad))
    ))
    Fnw = clip_val * np.tanh(Fnw / gradient)

    lcc = len(cmap_rgb)
    with np.errstate(invalid='ignore'):
        idx = np.clip(
            np.floor((ZI - caxis[0]) / (caxis[1] - caxis[0]) * lcc).astype(int),
            0, lcc - 1,
        )

    cc2 = cmap_rgb * 255.0
    Truecol = cc2[idx].astype(float)
    shade = Fnw[:, :, np.newaxis]
    Truecol = (
        Truecol * (1.0 - np.abs(shade))
        + 255.0 * shade * (shade > 0)
    )

    nan_mask = np.isnan(ZI) | np.isnan(dZdx) | np.isnan(dZdy)
    Truecol[nan_mask] = np.array(nan_color) * 255.0

    if lake_color is not None:
        lake_mask = (dZdx == 0.0) & (dZdy == 0.0) & ~nan_mask
        Truecol[lake_mask] = np.array(lake_color) * 255.0

    return np.clip(Truecol, 0.0, 255.0).astype(np.uint8)


def _resolve_cmap(colormap, ax):
    """Return an (n, 3) float array for the colormap."""
    if colormap is None:
        imgs = ax.get_images()
        colls = ax.collections
        if imgs:
            cmap_obj = imgs[-1].get_cmap()
        elif colls:
            cmap_obj = list(colls)[-1].get_cmap()
        else:
            cmap_obj = plt.get_cmap('viridis')
        return cmap_obj(np.linspace(0.0, 1.0, 256))[:, :3]
    elif isinstance(colormap, np.ndarray):
        return colormap.astype(float)
    else:
        return colormap(np.linspace(0.0, 1.0, 256))[:, :3]


def m_shadedrelief(
    lon,
    lat,
    Z,
    *,
    coords: str = 'geog',
    light_angle: float = -45.0,
    gradient: float = 10.0,
    clip_val: float = 0.9,
    smooth: int = 1,
    nan_color: tuple = (1.0, 1.0, 1.0),
    lake_color: tuple | None = None,
    colormap=None,
    caxis: tuple | None = None,
    resolution: int = 800,
):
    """
    Display shaded relief topography.

    Slopes facing the light source are brightened; slopes facing away are
    darkened.  The function must be preceded by m_proj().

    Parameters
    ----------
    lon : 1-D array-like
        Longitude vector (decimal degrees) for the columns of Z.
    lat : 1-D array-like
        Latitude vector (decimal degrees) for the rows of Z.
    Z : 2-D array-like, shape (len(lat), len(lon))
        Elevation in metres. NaN values produce white pixels.
    coords : {'geog', 'map', 'Z'}
        Coordinate system of lon/lat.  'geog' (default) treats them as
        geographic lat/lon; 'Z' treats them as already in metres.
    light_angle : float
        Compass direction of the light source in degrees (default –45 = NW).
    gradient : float
        Slope threshold in degrees — shading effect saturates at this slope.
    clip_val : float
        Maximum fractional change in brightness (0 = none, 1 = full).
    smooth : int
        Side-length of a box-average smoothing kernel for the gradient
        (must be an odd positive integer; 1 = no smoothing).
    nan_color : (r, g, b)
        RGB colour for NaN pixels, values in [0, 1].
    lake_color : (r, g, b) or None
        RGB colour for flat (zero-gradient) regions.  None = leave as-is.
    colormap : ndarray (n×3) or matplotlib Colormap or None
        RGB array or colormap to use.  If None, attempts to read from the
        current axes; if that fails, falls back to viridis.
    caxis : (vmin, vmax) or None
        Colour axis limits.  If None, uses Z.min() / Z.max().
    resolution : int
        Pixel resolution for the output image (used for circular/pseudo
        projections that require inverse reprojection).  Default 800.

    Returns
    -------
    matplotlib.image.AxesImage
    """
    from scipy.interpolate import RegularGridInterpolator

    state = get_state()

    lon = np.asarray(lon, dtype=float).ravel()
    lat = np.asarray(lat, dtype=float).ravel()
    Z = np.asarray(Z, dtype=float)

    if Z.ndim != 2:
        raise ValueError("Z must be a 2-D array.")
    if Z.shape != (len(lat), len(lon)):
        raise ValueError(
            f"Z shape {Z.shape} does not match (len(lat)={len(lat)}, len(lon)={len(lon)})."
        )

    if len(lon) == 2:
        lon = np.linspace(lon[0], lon[1], Z.shape[1])
    if len(lat) == 2:
        lat = np.linspace(lat[0], lat[1], Z.shape[0])

    ax = plt.gca()
    cmap_rgb = _resolve_cmap(colormap, ax)

    # ---------------------------------------------------------------------- #
    # For circular/pseudo projections (LAEA, orthographic, Mollweide, …),
    # geographic longitude and latitude do not map uniformly onto projected x/y,
    # so the simple forward-projection extent trick produces severe distortion.
    # Use inverse reprojection instead: build a regular grid in projected space,
    # inverse-project to geographic, interpolate Z there, then shade.
    # ---------------------------------------------------------------------- #
    if coords == 'geog' and state.projection_type in ('circular', 'pseudo'):
        # Ensure lat and lon are monotonically increasing for the interpolator
        if lat[-1] < lat[0]:
            lat = lat[::-1].copy()
            Z = Z[::-1].copy()
        if lon[-1] < lon[0]:
            lon = lon[::-1].copy()
            Z = Z[:, ::-1].copy()

        nx = ny = resolution
        xlm = np.linspace(float(state.x_limits[0]), float(state.x_limits[1]), nx)
        ylm = np.linspace(float(state.y_limits[0]), float(state.y_limits[1]), ny)
        XX, YY = np.meshgrid(xlm, ylm)

        HLG, HLT = m_xy2ll(XX, YY)

        if state.projection_type == 'circular':
            R_map = float(state.x_limits[1])
            outside = (XX**2 + YY**2) > R_map**2
        else:
            outside = ~np.isfinite(HLT) | ~np.isfinite(HLG)

        interp = RegularGridInterpolator(
            (lat, lon), Z, method='linear', bounds_error=False, fill_value=np.nan
        )
        pts = np.stack([HLT.ravel(), HLG.ravel()], axis=1)
        ZI = interp(pts).reshape(ny, nx)
        ZI[outside] = np.nan

        dx = (float(state.x_limits[1]) - float(state.x_limits[0])) / (nx - 1)
        dy = (float(state.y_limits[1]) - float(state.y_limits[0])) / (ny - 1)
        dZdy, dZdx = np.gradient(ZI, dy, dx)

        if smooth > 1:
            if smooth % 2 == 0:
                raise ValueError("'smooth' must be a positive odd integer.")
            from scipy.ndimage import uniform_filter
            dZdx = uniform_filter(dZdx, size=smooth, mode='nearest')
            dZdy = uniform_filter(dZdy, size=smooth, mode='nearest')

        Truecol = _shade_rgb(ZI, dZdx, dZdy, cmap_rgb, light_angle, gradient,
                             clip_val, nan_color, lake_color, caxis)
        # Outside pixels: transparent (white NaN fill is fine since the white
        # circle background sits behind at zorder=-1)
        Truecol[outside] = np.array(nan_color) * 255

        extent = [
            float(state.x_limits[0]), float(state.x_limits[1]),
            float(state.y_limits[0]), float(state.y_limits[1]),
        ]
        im = ax.imshow(Truecol, extent=extent, origin='lower',
                       aspect='auto', interpolation='none')
        return im

    # ---------------------------------------------------------------------- #
    # Rectangular / geographic projections: original forward-projection path.
    # ---------------------------------------------------------------------- #
    if coords == 'geog':
        if state.proj is None:
            raise RuntimeError("No map projection initialised — call m_proj() first.")
        x_map, _ = m_ll2xy(lon, np.full(len(lon), np.mean(lat)), clip='off')
        _, y_map = m_ll2xy(np.full(len(lat), np.mean(lon)), lat, clip='off')
    else:
        x_map = lon
        y_map = lat

    def _check_spacing(v, label):
        expected = np.linspace(v[0], v[-1], len(v))
        dev = np.max(np.abs(v - expected)) / abs(v[-1] - v[0])
        if dev > 0.005:
            # Usually not a mistake by the caller: projecting a regular lon/lat
            # grid gives non-uniform spacing on any projection that stretches
            # with latitude (Mercator most of all).  The relief is drawn on a
            # uniform raster, so the deviation quoted is the worst-case
            # positional error as a fraction of the map dimension — a few per
            # cent is normal and barely visible; a large value means the region
            # is too tall for one raster and should be split.
            warnings.warn(
                f"m_shadedrelief: projected {label} coordinates are not evenly "
                f"spaced (worst-case offset {dev:.1%} of the map {label} extent). "
                f"This is expected for a lon/lat grid on a stretching projection; "
                f"the shading is correct to within that offset."
            )

    _check_spacing(x_map, 'X')
    _check_spacing(y_map, 'Y')

    dZdy, dZdx = np.gradient(Z, y_map, x_map)

    if smooth > 1:
        if smooth % 2 == 0:
            raise ValueError("'smooth' must be a positive odd integer.")
        from scipy.ndimage import uniform_filter
        dZdx = uniform_filter(dZdx, size=smooth, mode='nearest')
        dZdy = uniform_filter(dZdy, size=smooth, mode='nearest')

    Truecol = _shade_rgb(Z, dZdx, dZdy, cmap_rgb, light_angle, gradient,
                         clip_val, nan_color, lake_color, caxis)

    extent = [x_map[0], x_map[-1], y_map[0], y_map[-1]]
    im = ax.imshow(Truecol, extent=extent, origin='lower',
                   aspect='auto', interpolation='none')
    return im
