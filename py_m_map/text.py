"""
Geographic text placement: m_text.

Ported from m_text.m (R. Pawlowicz, UBC EOAS).
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from .projection import m_ll2xy
from ._state import get_state


def m_text(lon: float, lat: float, s, **kwargs):
    """
    Place text at a geographic position on the current map.

    Parameters
    ----------
    lon, lat : float
        Position in decimal degrees.
    s : str or list of str
        Text string.  A list is joined with newlines (mirrors MATLAB
        cell-array behaviour).
    **kwargs
        Forwarded to ``ax.text()``.

    Returns
    -------
    matplotlib.text.Text
    """
    state = get_state()
    if state.proj is None:
        raise RuntimeError("No map projection initialised — call m_proj() first.")

    x, y = m_ll2xy(np.atleast_1d(float(lon)), np.atleast_1d(float(lat)),
                   clip='off')
    x = float(np.asarray(x).ravel()[0])
    y = float(np.asarray(y).ravel()[0])

    if isinstance(s, (list, tuple)):
        s = '\n'.join(str(item) for item in s)
    else:
        s = str(s)

    kw: dict = {'ha': 'center', 'va': 'center'}
    kw.update(kwargs)

    ax = plt.gca()
    return ax.text(x, y, s, **kw)


def m_title(text: str, ax=None, **kwargs):
    """
    Set a map title that correctly clears the outer ruler border when
    ``m_grid(box='fancy')`` has been called.

    Parameters
    ----------
    text : str
        Title string.
    ax : matplotlib.axes.Axes, optional
        Target axes.  Defaults to ``plt.gca()``.
    **kwargs
        Forwarded to ``ax.set_title()``.

    Returns
    -------
    matplotlib.text.Text
    """
    state = get_state()
    if ax is None:
        ax = plt.gca()
    title_y = state.title_y if state.title_y is not None else 1.0
    kwargs.setdefault('y', title_y)
    return ax.set_title(text, **kwargs)
