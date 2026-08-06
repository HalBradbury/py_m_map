"""
py_m_map — Python port of m_map (Rich Pawlowicz, UBC EOAS).

Phase 1 public API:
    m_proj          — initialise a map projection
    m_ll2xy         — geographic → map coordinates
    m_xy2ll         — map → geographic coordinates
    m_colmap        — custom colormaps
    m_shadedrelief  — shaded relief topography
    m_contourf      — filled contours
    m_contour       — contour lines
    m_grid          — map frame and tick labels
    m_contfbar      — colourbar for contourf / shaded relief
"""

from importlib.metadata import PackageNotFoundError, version as _pkg_version

try:
    __version__ = _pkg_version('py_m_map')
except PackageNotFoundError:      # running from a source tree, not installed
    __version__ = '0.0.0.dev0'

from ._state import get_state, reset_state
from .projection import m_proj, m_ll2xy, m_xy2ll
from .colormaps import m_colmap
from .shaded_relief import m_shadedrelief
from .contour import m_contourf, m_contour
from .grid import m_grid
from .colorbar import m_contfbar
from .coast import m_coast, m_landmask
from .elevation import m_elev
from .etopo import m_etopo2
from .quiver import m_quiver
from .line import m_line
from .northarrow import m_northarrow
from .vec import m_vec
from .gshhs import m_gshhs, m_gshhs_c, m_gshhs_l, m_gshhs_i, m_gshhs_h, m_gshhs_f
from .decorations import m_ruler, m_utmgrid
from .track import m_track
from .range_ring import m_range_ring
from .hatch import m_hatch
from .text import m_text, m_title
from .geodesic import m_lldist, m_idist, m_fdist, m_xydist
from .pcolor import m_pcolor
from .image import m_image
from .usercoast import m_usercoast
from .windbarb import m_windbarb
from .windrose import m_windrose

__all__ = [
    '__version__',
    'get_state', 'reset_state',
    'm_proj', 'm_ll2xy', 'm_xy2ll',
    'm_colmap',
    'm_shadedrelief',
    'm_contourf', 'm_contour',
    'm_grid',
    'm_contfbar',
    'm_coast', 'm_landmask',
    'm_elev',
    'm_etopo2',
    'm_quiver',
    'm_line',
    'm_northarrow',
    'm_vec',
    'm_gshhs', 'm_gshhs_c', 'm_gshhs_l', 'm_gshhs_i', 'm_gshhs_h', 'm_gshhs_f',
    'm_ruler',
    'm_utmgrid',
    'm_track',
    'm_range_ring',
    'm_hatch',
    'm_text', 'm_title',
    'm_lldist', 'm_idist', 'm_fdist', 'm_xydist',
    'm_pcolor',
    'm_image',
    'm_usercoast',
    'm_windbarb',
    'm_windrose',
]
