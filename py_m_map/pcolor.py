"""
m_pcolor — pseudocolour plot of gridded data on a map projection.
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def m_pcolor(lon, lat, data, **kwargs):
    """
    Pseudocolor (pcolormesh) plot of gridded data on a map.

    Parameters
    ----------
    lon, lat : array-like
        Longitude and latitude.  If both are 1-D they are automatically
        meshgridded.  Normally the *same shape* as ``data``, in which case
        ``shading='auto'`` treats them as cell **centres** and infers the cell
        edges from the midpoints between them — no data is dropped, matching
        MATLAB ``shading flat``.  Supply arrays one larger than ``data`` in each
        dimension to give the cell **edges** explicitly instead.
    data : array-like
        Scalar field to colour.
    **kwargs
        Forwarded to ``ax.pcolormesh``.  ``edgecolor`` defaults to ``'none'``
        and ``shading`` defaults to ``'auto'``.

    Notes
    -----
    The coordinates are projected before being handed to pcolormesh, so on any
    non-rectangular projection they are curvilinear and generally not monotonic
    along a row or column.  matplotlib then emits "coordinates are not
    monotonically increasing or decreasing"; the output is still correct, since
    the edge midpoints of a smooth curvilinear grid remain well defined.  Pass
    explicit edge arrays if you would rather not see the warning.

    Cells that fall outside the map, or that straddle the projection's cut
    meridian, are drawn fully transparent rather than being handed to the
    colormap's "bad" colour.  A colour set with ``cmap.set_bad`` therefore marks
    only the missing values in *your* data, and never leaks onto the parts of the
    grid that simply are not on this map.  If ``alpha`` is given it applies to the
    visible cells as usual.

    Returns
    -------
    h : matplotlib.collections.QuadMesh
    """
    state = get_state()

    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    data = np.asarray(data, dtype=float)

    if lon.ndim == 1 and lat.ndim == 1:
        lon, lat = np.meshgrid(lon, lat)

    # Cells to hide because they are not on the map — as distinct from cells the
    # caller's own data marks as missing.  See the note below on why the two are
    # kept apart.
    hidden = np.zeros(data.shape, dtype=bool)

    # Identify out-of-bounds points using clip='on'
    X, Y = m_ll2xy(lon, lat, clip='on')
    outside = np.isnan(X)

    data = data.copy()

    if outside.any():
        if outside.shape == data.shape:
            hidden |= outside
        else:
            # lon/lat are cell-edge (M+1, N+1); data is (M, N)
            m, n = data.shape
            hidden |= (
                outside[:m, :n] | outside[:m, 1:n+1] |
                outside[1:m+1, :n] | outside[1:m+1, 1:n+1]
            )
        # Re-project without NaN-ification: pcolormesh rejects non-finite
        # coordinates outright, so the grid handed to it must stay regular.
        X, Y = m_ll2xy(lon, lat, clip='patch')

    # Hide cells that span the antimeridian / projection cut (x-jump > 50% map width)
    x_range = float(state.x_limits[1]) - float(state.x_limits[0])
    if x_range > 0 and X.shape == data.shape:
        dx_col = np.abs(np.diff(X, axis=1))
        jump_col = dx_col > 0.5 * x_range  # shape (M, N-1)
        if jump_col.any():
            cols = np.where(np.any(jump_col, axis=0))[0]
            for j in cols:
                hidden[:, j] = True
                hidden[:, j + 1] = True
        dx_row = np.abs(np.diff(X, axis=0))
        jump_row = dx_row > 0.5 * x_range
        if jump_row.any():
            rows = np.where(np.any(jump_row, axis=1))[0]
            for i in rows:
                hidden[i, :] = True
                hidden[i + 1, :] = True

    kwargs.setdefault('edgecolor', 'none')
    kwargs.setdefault('shading', 'auto')

    if hidden.any():
        # Make off-map cells transparent rather than merely NaN.
        #
        # NaN would send them through the colormap's "bad" colour, which is the
        # same channel the caller's own missing data uses.  That conflates two
        # unrelated things: with an opaque set_bad (grey land, say) every off-map
        # cell is painted too, and a call whose data lies entirely outside the map
        # covers the whole figure in that colour.  Per-cell alpha keeps the two
        # separate — off-map cells vanish whatever the colormap says, while the
        # caller's NaNs still render as "bad".
        #
        # They are also set to NaN so they take no part in colour autoscaling.
        data[hidden] = np.nan
        alpha = kwargs.pop('alpha', None)
        visible = 1.0 if alpha is None else alpha
        kwargs['alpha'] = np.where(hidden, 0.0,
                                   np.broadcast_to(visible, data.shape))

    ax = plt.gca()
    return ax.pcolormesh(X, Y, data, **kwargs)
