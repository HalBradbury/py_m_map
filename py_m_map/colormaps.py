"""
Custom colormaps ported from m_map's m_colmap.m.

m_colmap(name, n) returns a matplotlib ListedColormap.

Supported names (prefix-matched, case-insensitive):
    'blues' / 'blue'  — perceptually uniform dark-to-light blue (for bathymetry)
    'green'           — dark green → pale green (chlorophyll / land)
    'diverging'       — dark blue → white → dark magenta (currents, echo-sounder)
    'gland'           — green→brown→grey→white topographic ramp (for land, green stretched)
    'land'            — green→brown→grey→white (green compressed near sea level)
    'bland'           — brown→grey→white (land without green, starts at sea level)
    'water'           — ETOPO1 deep-navy to pale-blue ocean colormap
    'depth'           — red (deep) → yellow → green → cyan → blue → white (shallow)
    'odv'             — CET isoluminant rainbow (magenta→cyan→green→yellow→orange)
    '1cyclic'         — CET cyclic (yellow→green→blue→purple→yellow)
    '2cyclic'         — CET cyclic with two dark regions (pink→brown→cyan→purple→pink)
    'chlorophyll'     — light green → dark green → yellow → orange → red
    'CBchlorophyll'   — colorblind-friendly chlorophyll (pale green → magenta)
    'EK80'            — echo-sounder standard (mauve→blue→cyan→green→yellow→red)
    'BOD'             — blue-orange diverging (dark blue → white → dark orange)
    'mBOD'            — modified blue-orange diverging (no white middle)
    'rBOD'            — reversed blue-orange with grey midpoint
"""
from __future__ import annotations
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ---------------------------------------------------------------------------
# 'gland' colormap — 20 RGB anchor points, r = linspace(0, 255, 20)
# Extracted verbatim from m_colmap.m (gland case, lines ~1298-1324).
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# 'green' colormap — 32 anchor points sampled from m_colmap.m's 256-row table.
# Dark green (low Chla / low elevation) → pale green-white (high values).
# ---------------------------------------------------------------------------
_GREEN_RGB = np.array([
    [0.00000, 0.26667, 0.10588],
    [0.00000, 0.30980, 0.12157],
    [0.00000, 0.35294, 0.13725],
    [0.00000, 0.39608, 0.15686],
    [0.00000, 0.43137, 0.17647],
    [0.01961, 0.46275, 0.19608],
    [0.05882, 0.49020, 0.22353],
    [0.10980, 0.52157, 0.25098],
    [0.14510, 0.55294, 0.27843],
    [0.17255, 0.58431, 0.30196],
    [0.20000, 0.61569, 0.32157],
    [0.22745, 0.64706, 0.34510],
    [0.27059, 0.68235, 0.37255],
    [0.31765, 0.70588, 0.39608],
    [0.37647, 0.73333, 0.42353],
    [0.43137, 0.75686, 0.44706],
    [0.48627, 0.78431, 0.48235],
    [0.52941, 0.80392, 0.51765],
    [0.57255, 0.82353, 0.55686],
    [0.61569, 0.84314, 0.59216],
    [0.66275, 0.86275, 0.63529],
    [0.70196, 0.88235, 0.67059],
    [0.73725, 0.89412, 0.70980],
    [0.77255, 0.90980, 0.74510],
    [0.80392, 0.92549, 0.77647],
    [0.83922, 0.93725, 0.81569],
    [0.87059, 0.94902, 0.84706],
    [0.89412, 0.96078, 0.87451],
    [0.91765, 0.96863, 0.89804],
    [0.93725, 0.97647, 0.92549],
    [0.95686, 0.98431, 0.94510],
    [0.96863, 0.98824, 0.96078],
], dtype=np.float32)

_GREEN_R = np.linspace(0.0, 255.0, len(_GREEN_RGB))


# ---------------------------------------------------------------------------
# 'diverging' colormap — 32 anchor points sampled from m_colmap.m's 256-row
# table (which is stored reversed, then flipud'd).
# Dark blue → light blue → white → light pink → dark magenta.
# ---------------------------------------------------------------------------
_DIV_RGB = np.array([
    [0.01961, 0.18824, 0.38039],
    [0.05098, 0.25882, 0.50196],
    [0.08627, 0.32941, 0.60000],
    [0.12941, 0.40000, 0.67451],
    [0.16471, 0.45490, 0.70980],
    [0.20392, 0.50980, 0.73333],
    [0.24706, 0.56078, 0.75686],
    [0.33333, 0.63137, 0.79608],
    [0.44314, 0.69804, 0.83137],
    [0.54902, 0.76078, 0.86275],
    [0.63529, 0.80784, 0.89020],
    [0.71765, 0.84706, 0.91373],
    [0.79608, 0.88627, 0.93725],
    [0.85882, 0.91765, 0.94902],
    [0.91373, 0.94510, 0.96078],
    [0.95686, 0.96471, 0.96863],
    [0.97647, 0.96078, 0.95686],
    [0.98431, 0.93333, 0.90196],
    [0.99216, 0.88627, 0.82745],
    [0.99216, 0.83922, 0.75294],
    [0.98039, 0.76863, 0.65098],
    [0.96863, 0.69412, 0.56078],
    [0.94902, 0.61961, 0.48235],
    [0.91765, 0.53725, 0.41176],
    [0.87451, 0.45098, 0.34902],
    [0.82745, 0.35294, 0.29020],
    [0.78824, 0.25098, 0.23922],
    [0.74510, 0.15294, 0.19608],
    [0.69020, 0.09020, 0.16471],
    [0.60784, 0.04314, 0.14118],
    [0.51373, 0.01176, 0.12941],
    [0.40392, 0.00000, 0.12157],
], dtype=np.float32)

_DIV_R = np.linspace(0.0, 255.0, len(_DIV_RGB))


# ---------------------------------------------------------------------------
# 'gland' colormap — 20 RGB anchor points, r = linspace(0, 255, 20)
# Extracted verbatim from m_colmap.m (gland case, lines ~1298-1324).
# ---------------------------------------------------------------------------
_GLAND_RGB = np.array([
    [0.20000, 0.40000, 0.00000],   # dark green  (low elevation)
    [0.20000, 0.80000, 0.40000],   # mid green
    [0.73333, 0.89412, 0.57255],   # light green
    [1.00000, 0.86275, 0.72549],   # pale tan
    [0.95294, 0.79216, 0.53725],   # tan
    [0.90196, 0.72157, 0.34510],   # light brown
    [0.85098, 0.65098, 0.15294],   # yellow-brown
    [0.65882, 0.60392, 0.12157],   # brown
    [0.64314, 0.56471, 0.09804],
    [0.63529, 0.52549, 0.07451],
    [0.62353, 0.48235, 0.05098],
    [0.61176, 0.44314, 0.02745],
    [0.60000, 0.40000, 0.00000],   # dark brown
    [0.63529, 0.34902, 0.34902],   # reddish-grey
    [0.69804, 0.46275, 0.46275],
    [0.71765, 0.57647, 0.57647],
    [0.76078, 0.69020, 0.69020],
    [0.80000, 0.80000, 0.80000],   # light grey
    [0.89804, 0.89804, 0.89804],   # near white
    [1.00000, 1.00000, 1.00000],   # white (snow/high elevation)
], dtype=np.float32)

_GLAND_R = np.linspace(0.0, 255.0, len(_GLAND_RGB))

# 'land' uses the same anchor RGB values as 'gland' but with non-linear r
# derived from the first column of the MATLAB Data matrix (ETOPO1 elevation
# levels): r = (col1 - col1_min) / (col1_max - col1_min) * 255.
# This compresses the green band near sea level and stretches the upper range.
_LAND_R_COL = np.array([
    0.56410, 0.56920, 0.57440, 0.58970, 0.61540, 0.64100,
    0.66670, 0.69230, 0.71790, 0.74360, 0.76920, 0.79490,
    0.82050, 0.84620, 0.87180, 0.89740, 0.92310, 0.94870,
    0.97440, 1.00000,
], dtype=np.float64)
_LAND_R = ((_LAND_R_COL - _LAND_R_COL[0]) /
           (_LAND_R_COL[-1] - _LAND_R_COL[0]) * 255.0)

# 'bland' = land without the 3 green anchor rows; starts at pale tan (sea level)
_BLAND_RGB = _GLAND_RGB[3:]    # rows 3-19 → pale tan through white
_BLAND_R_COL = _LAND_R_COL[3:]
_BLAND_R = ((_BLAND_R_COL - _BLAND_R_COL[0]) /
            (_BLAND_R_COL[-1] - _BLAND_R_COL[0]) * 255.0)


# ---------------------------------------------------------------------------
# 'water' colormap — ETOPO1 ocean shading (dark navy → pale blue)
# Extracted verbatim from m_colmap.m (water case, lines ~1271-1296).
# r values are the first column (normalised to 0–255 internally).
# ---------------------------------------------------------------------------
_WATER_R_RAW = np.array([
    0.00000, 0.02560, 0.05130, 0.07690, 0.10260, 0.12820, 0.15380,
    0.17950, 0.20510, 0.23080, 0.25640, 0.28210, 0.30770, 0.33330,
    0.35900, 0.38460, 0.41030, 0.43590, 0.46150, 0.48720, 0.51280,
    0.53850, 0.56410,
], dtype=np.float64)
_WATER_RGB = np.array([
    [0.03922, 0.00000, 0.47451],
    [0.10196, 0.00000, 0.53725],
    [0.14902, 0.00000, 0.59608],
    [0.10588, 0.01176, 0.65098],
    [0.06275, 0.02353, 0.70588],
    [0.01961, 0.03529, 0.75686],
    [0.00000, 0.05490, 0.79608],
    [0.00000, 0.08627, 0.82353],
    [0.00000, 0.11765, 0.84706],
    [0.00000, 0.15294, 0.87451],
    [0.04706, 0.26667, 0.90588],
    [0.10196, 0.40000, 0.94118],
    [0.07451, 0.45882, 0.95686],
    [0.05490, 0.52157, 0.97647],
    [0.08235, 0.61961, 0.98824],
    [0.11765, 0.69804, 1.00000],
    [0.16863, 0.72941, 1.00000],
    [0.21569, 0.75686, 1.00000],
    [0.25490, 0.78431, 1.00000],
    [0.30980, 0.82353, 1.00000],
    [0.36863, 0.87451, 1.00000],
    [0.54118, 0.89020, 1.00000],
    [0.73725, 0.90196, 1.00000],
], dtype=np.float32)
_WATER_R = ((_WATER_R_RAW - _WATER_R_RAW[0]) /
            (_WATER_R_RAW[-1] - _WATER_R_RAW[0]) * 255.0)


# ---------------------------------------------------------------------------
# 'depth' colormap — red (deep, -6000 m) → yellow → green → cyan → blue →
#                    white (shallow, 0 m)
# Designed for ocean bathymetry displayed with caxis=(-6000, 0):
# colormap index 0 maps to the deepest (reddest) colour.
# ---------------------------------------------------------------------------
_DEPTH_RGB = np.array([
    [1.00000, 0.00000, 0.00000],   # red        (deepest)
    [1.00000, 0.50000, 0.00000],   # orange
    [1.00000, 1.00000, 0.00000],   # yellow
    [0.00000, 0.75000, 0.00000],   # green
    [0.00000, 0.75000, 1.00000],   # cyan
    [0.00000, 0.25000, 1.00000],   # blue
    [1.00000, 1.00000, 1.00000],   # white      (shallowest)
], dtype=np.float32)

_DEPTH_R = np.linspace(0.0, 255.0, len(_DEPTH_RGB))


# ---------------------------------------------------------------------------
# 'odv' — CET isoluminant rainbow (32 anchors from 256-row table)
# ---------------------------------------------------------------------------
_ODV_RGB = np.array([
    [0.90101, 0.00000, 0.93251],
    [0.83028, 0.20704, 0.95136],
    [0.75444, 0.29193, 0.96876],
    [0.66103, 0.35849, 0.98591],
    [0.56818, 0.40464, 0.99786],
    [0.46239, 0.44281, 1.00000],
    [0.35727, 0.47310, 0.99362],
    [0.30813, 0.49424, 0.94565],
    [0.30771, 0.50644, 0.89083],
    [0.32370, 0.51556, 0.83150],
    [0.34393, 0.52294, 0.76993],
    [0.36319, 0.52925, 0.70715],
    [0.37916, 0.53586, 0.63616],
    [0.38490, 0.54206, 0.57372],
    [0.38335, 0.54857, 0.51187],
    [0.37464, 0.55539, 0.45047],
    [0.35554, 0.56352, 0.38171],
    [0.32817, 0.57124, 0.32065],
    [0.28586, 0.57968, 0.25974],
    [0.26173, 0.58494, 0.18282],
    [0.35918, 0.57299, 0.11036],
    [0.44224, 0.55716, 0.09495],
    [0.51378, 0.53935, 0.08834],
    [0.57858, 0.51938, 0.08229],
    [0.63892, 0.49686, 0.07680],
    [0.70309, 0.46786, 0.07178],
    [0.75770, 0.43802, 0.06836],
    [0.81061, 0.40321, 0.06606],
    [0.86221, 0.36168, 0.06509],
    [0.91900, 0.30274, 0.06561],
    [0.96862, 0.23073, 0.06753],
    [1.00000, 0.10393, 0.07071],
], dtype=np.float32)
_ODV_R = np.linspace(0.0, 255.0, len(_ODV_RGB))

# ---------------------------------------------------------------------------
# '2cyclic' — CET cyclic with two dark regions (32 anchors from 256-row table)
# ---------------------------------------------------------------------------
_CYCLIC2_RGB = np.array([
    [0.97561, 0.52012, 0.97096],
    [0.99221, 0.47844, 0.88563],
    [0.97879, 0.41120, 0.77068],
    [0.95055, 0.32780, 0.63745],
    [0.91398, 0.25557, 0.51908],
    [0.86383, 0.19250, 0.39903],
    [0.80486, 0.13567, 0.27982],
    [0.74022, 0.08926, 0.15426],
    [0.70983, 0.12104, 0.06800],
    [0.72021, 0.20107, 0.02273],
    [0.74979, 0.28311, 0.01614],
    [0.78044, 0.35925, 0.01818],
    [0.80876, 0.44276, 0.01903],
    [0.82704, 0.51694, 0.01657],
    [0.83985, 0.58906, 0.01992],
    [0.83647, 0.64850, 0.08264],
    [0.78178, 0.66795, 0.21520],
    [0.68818, 0.64226, 0.33397],
    [0.57126, 0.60423, 0.43817],
    [0.42978, 0.56493, 0.53322],
    [0.24249, 0.51265, 0.63755],
    [0.13380, 0.44458, 0.73395],
    [0.16246, 0.35387, 0.83257],
    [0.21650, 0.26578, 0.91830],
    [0.29964, 0.23933, 0.96530],
    [0.40009, 0.29250, 0.97742],
    [0.47824, 0.35535, 0.97849],
    [0.56311, 0.40995, 0.98111],
    [0.66757, 0.45099, 0.98786],
    [0.79361, 0.48821, 0.99807],
    [0.89709, 0.51633, 1.00000],
    [0.97003, 0.52229, 0.97779],
], dtype=np.float32)
_CYCLIC2_R = np.linspace(0.0, 255.0, len(_CYCLIC2_RGB))

# ---------------------------------------------------------------------------
# '1cyclic' — CET cyclic with one dark region (32 anchors from 256-row table)
# ---------------------------------------------------------------------------
_CYCLIC1_RGB = np.array([
    [0.94370, 0.93240, 0.20920],
    [0.87010, 0.92820, 0.11980],
    [0.78030, 0.89930, 0.08750],
    [0.67530, 0.86080, 0.07380],
    [0.57910, 0.82600, 0.06300],
    [0.47800, 0.79060, 0.05260],
    [0.36800, 0.75470, 0.04660],
    [0.24120, 0.71110, 0.08690],
    [0.19550, 0.66440, 0.18590],
    [0.23590, 0.60910, 0.30570],
    [0.26840, 0.55020, 0.42130],
    [0.26600, 0.49100, 0.52920],
    [0.22410, 0.42300, 0.64350],
    [0.17840, 0.35580, 0.73480],
    [0.15220, 0.27500, 0.81470],
    [0.14650, 0.18330, 0.88480],
    [0.23040, 0.10790, 0.93740],
    [0.34140, 0.12020, 0.95800],
    [0.43810, 0.16510, 0.97000],
    [0.52550, 0.20780, 0.97970],
    [0.63120, 0.24220, 0.98520],
    [0.73440, 0.25960, 0.98410],
    [0.83420, 0.27520, 0.97910],
    [0.91570, 0.30980, 0.96180],
    [0.96290, 0.38550, 0.91420],
    [0.98260, 0.49430, 0.82890],
    [0.98720, 0.58590, 0.74410],
    [0.98660, 0.66950, 0.65650],
    [0.98650, 0.74530, 0.56630],
    [0.98870, 0.82360, 0.45760],
    [0.98310, 0.88750, 0.34670],
    [0.95060, 0.92990, 0.22390],
], dtype=np.float32)
_CYCLIC1_R = np.linspace(0.0, 255.0, len(_CYCLIC1_RGB))

# ---------------------------------------------------------------------------
# 'chlorophyll' — light green → dark green → yellow → orange → red
#                 (32 anchors from 256-row table)
# ---------------------------------------------------------------------------
_CHLOROPHYLL_RGB = np.array([
    [0.89670, 0.96400, 0.86680],
    [0.83190, 0.91740, 0.79480],
    [0.76760, 0.87110, 0.72360],
    [0.69560, 0.81930, 0.64480],
    [0.63200, 0.77370, 0.57580],
    [0.56860, 0.72830, 0.50780],
    [0.50530, 0.68330, 0.44060],
    [0.43370, 0.63300, 0.36610],
    [0.36960, 0.58910, 0.30060],
    [0.30690, 0.55020, 0.23760],
    [0.25300, 0.52840, 0.18350],
    [0.21970, 0.53750, 0.14800],
    [0.20880, 0.58110, 0.13160],
    [0.21050, 0.63310, 0.12680],
    [0.21570, 0.68820, 0.12270],
    [0.24250, 0.74260, 0.11730],
    [0.36690, 0.79540, 0.11310],
    [0.56740, 0.82080, 0.11600],
    [0.77850, 0.81100, 0.12150],
    [0.92450, 0.76300, 0.11590],
    [0.99230, 0.68060, 0.08890],
    [1.00000, 0.59760, 0.05200],
    [1.00000, 0.50900, 0.01100],
    [1.00000, 0.41300, 0.00000],
    [0.99280, 0.31070, 0.00000],
    [0.94950, 0.20420, 0.00000],
    [0.88580, 0.13800, 0.00000],
    [0.81040, 0.09690, 0.00000],
    [0.73280, 0.06370, 0.00000],
    [0.64690, 0.02390, 0.00000],
    [0.57250, 0.00000, 0.00000],
    [0.50000, 0.00000, 0.00000],
], dtype=np.float32)
_CHLOROPHYLL_R = np.linspace(0.0, 255.0, len(_CHLOROPHYLL_RGB))

# ---------------------------------------------------------------------------
# 'EK80' — echo-sounder standard (32 anchors from 64-row table)
# ---------------------------------------------------------------------------
_EK80_RGB = np.array([
    [0.61176, 0.54118, 0.65882],
    [0.49412, 0.44314, 0.51765],
    [0.38039, 0.34510, 0.37647],
    [0.26667, 0.29804, 0.36863],
    [0.15294, 0.35294, 0.63922],
    [0.03529, 0.40392, 0.90980],
    [0.03529, 0.32941, 0.91765],
    [0.08627, 0.18824, 0.80000],
    [0.14118, 0.04706, 0.68235],
    [0.14902, 0.33725, 0.61176],
    [0.15686, 0.62745, 0.54118],
    [0.14510, 0.78431, 0.47843],
    [0.09412, 0.67059, 0.43529],
    [0.03922, 0.55294, 0.38824],
    [0.26667, 0.63529, 0.32157],
    [0.63137, 0.81569, 0.24314],
    [0.99608, 0.89804, 0.16863],
    [0.99216, 0.70196, 0.17647],
    [0.98824, 0.50196, 0.18431],
    [0.98824, 0.43137, 0.33333],
    [0.98824, 0.38824, 0.50980],
    [0.98824, 0.33333, 0.62745],
    [0.99216, 0.23922, 0.46275],
    [0.99608, 0.14118, 0.29412],
    [0.94118, 0.11765, 0.20392],
    [0.83137, 0.17255, 0.19608],
    [0.72157, 0.22353, 0.18824],
    [0.66667, 0.21176, 0.20000],
    [0.62353, 0.18431, 0.21961],
    [0.58824, 0.15294, 0.21961],
    [0.60000, 0.09020, 0.12941],
    [0.60784, 0.02745, 0.04314],
], dtype=np.float32)
_EK80_R = np.linspace(0.0, 255.0, len(_EK80_RGB))

# ---------------------------------------------------------------------------
# 'BOD' — blue-orange diverging (32 anchors from 256-row table)
# ---------------------------------------------------------------------------
_BOD_RGB = np.array([
    [0.08627, 0.00392, 0.29804],
    [0.11340, 0.02466, 0.45340],
    [0.07835, 0.04612, 0.53085],
    [0.03714, 0.13072, 0.61922],
    [0.05457, 0.24093, 0.67733],
    [0.05490, 0.31609, 0.70915],
    [0.05178, 0.38013, 0.73479],
    [0.03845, 0.47359, 0.77055],
    [0.03137, 0.56378, 0.79619],
    [0.02724, 0.66533, 0.82211],
    [0.04277, 0.77303, 0.84512],
    [0.08246, 0.85781, 0.87010],
    [0.40570, 0.93683, 0.87321],
    [0.58007, 0.96607, 0.83598],
    [0.73728, 0.98039, 0.86057],
    [0.89040, 0.98824, 0.92559],
    [0.99005, 0.98097, 0.85865],
    [0.98974, 0.95988, 0.67029],
    [0.97856, 0.91092, 0.49390],
    [0.95692, 0.84407, 0.35633],
    [0.92085, 0.75078, 0.25959],
    [0.89367, 0.66926, 0.20303],
    [0.87536, 0.59193, 0.16401],
    [0.85790, 0.50081, 0.14925],
    [0.83330, 0.41792, 0.13449],
    [0.80438, 0.32049, 0.10757],
    [0.76148, 0.21984, 0.08297],
    [0.69919, 0.13587, 0.06482],
    [0.61369, 0.05979, 0.04544],
    [0.49616, 0.01952, 0.08380],
    [0.39014, 0.00374, 0.10050],
    [0.18824, 0.00000, 0.07059],
], dtype=np.float32)
_BOD_R = np.linspace(0.0, 255.0, len(_BOD_RGB))

# ---------------------------------------------------------------------------
# 'mBOD' — modified blue-orange diverging (32 anchors from 225-row table)
# ---------------------------------------------------------------------------
_MBOD_RGB = np.array([
    [0.08627, 0.00392, 0.29804],
    [0.11112, 0.02167, 0.43644],
    [0.10608, 0.05030, 0.50834],
    [0.03308, 0.08521, 0.59145],
    [0.04677, 0.18891, 0.65132],
    [0.05490, 0.26951, 0.68953],
    [0.05417, 0.33227, 0.71565],
    [0.05098, 0.39608, 0.74118],
    [0.03845, 0.47359, 0.77055],
    [0.03137, 0.55199, 0.79266],
    [0.02954, 0.63772, 0.81636],
    [0.03069, 0.73334, 0.83649],
    [0.06128, 0.82884, 0.86128],
    [0.22902, 0.89370, 0.86412],
    [0.45491, 0.94613, 0.86625],
    [0.59835, 0.96940, 0.83764],
    [0.98053, 0.91834, 0.51218],
    [0.96440, 0.86351, 0.38923],
    [0.93553, 0.79115, 0.29189],
    [0.91130, 0.72214, 0.23859],
    [0.88493, 0.64128, 0.18380],
    [0.87289, 0.56978, 0.16032],
    [0.85482, 0.48912, 0.14740],
    [0.83330, 0.41792, 0.13449],
    [0.81176, 0.34510, 0.11373],
    [0.77624, 0.24568, 0.08912],
    [0.72318, 0.16355, 0.07036],
    [0.65836, 0.09719, 0.05390],
    [0.57819, 0.04204, 0.05924],
    [0.46711, 0.01511, 0.09078],
    [0.36490, 0.00327, 0.09676],
    [0.18824, 0.00000, 0.07059],
], dtype=np.float32)
_MBOD_R = np.linspace(0.0, 255.0, len(_MBOD_RGB))

# ---------------------------------------------------------------------------
# 'rBOD' — reversed blue-orange with grey midpoint (32 anchors from 256-row)
# ---------------------------------------------------------------------------
_RBOD_RGB = np.array([
    [0.30900, 0.84420, 0.94170],
    [0.39640, 0.79540, 0.91780],
    [0.45910, 0.74630, 0.89390],
    [0.51280, 0.69050, 0.86720],
    [0.55070, 0.64030, 0.84340],
    [0.58160, 0.58930, 0.81980],
    [0.60700, 0.53700, 0.79620],
    [0.63030, 0.47620, 0.76980],
    [0.64700, 0.41940, 0.74640],
    [0.66040, 0.35860, 0.72300],
    [0.66950, 0.29250, 0.69870],
    [0.65510, 0.24250, 0.65950],
    [0.58260, 0.25100, 0.57670],
    [0.50060, 0.26870, 0.49240],
    [0.41800, 0.27760, 0.40970],
    [0.34660, 0.27910, 0.33310],
    [0.36380, 0.27720, 0.29050],
    [0.45930, 0.27150, 0.29540],
    [0.56220, 0.25650, 0.30670],
    [0.66330, 0.22930, 0.31830],
    [0.75950, 0.20260, 0.32710],
    [0.80160, 0.23830, 0.32280],
    [0.82470, 0.29550, 0.31240],
    [0.84600, 0.34900, 0.30040],
    [0.86680, 0.39920, 0.28680],
    [0.88950, 0.45340, 0.26930],
    [0.90910, 0.50020, 0.25130],
    [0.92820, 0.54620, 0.23020],
    [0.94670, 0.59160, 0.20510],
    [0.96700, 0.64210, 0.16950],
    [0.98440, 0.68680, 0.12610],
    [1.00000, 0.73130, 0.05220],
], dtype=np.float32)
_RBOD_R = np.linspace(0.0, 255.0, len(_RBOD_RGB))

# ---------------------------------------------------------------------------
# 'CBchlorophyll' — colorblind-friendly chlorophyll (pale green → magenta)
# 32 anchors sampled from the 256-row table in m_colmap.m (chlorophyll2 case).
# ---------------------------------------------------------------------------
_CBCHL_RGB = np.array([
    [0.94330, 0.94350, 0.94350],
    [0.85960, 0.92900, 0.83860],
    [0.77310, 0.91320, 0.73440],
    [0.67080, 0.89370, 0.61740],
    [0.57320, 0.87490, 0.51290],
    [0.46810, 0.85420, 0.40880],
    [0.36330, 0.82970, 0.31450],
    [0.27280, 0.79570, 0.24020],
    [0.22360, 0.76150, 0.20120],
    [0.18510, 0.72630, 0.17090],
    [0.14500, 0.69130, 0.14090],
    [0.10250, 0.65640, 0.11140],
    [0.08710, 0.61590, 0.09560],
    [0.13930, 0.57690, 0.11940],
    [0.20400, 0.53490, 0.16270],
    [0.25340, 0.49150, 0.20410],
    [0.29140, 0.44220, 0.24310],
    [0.31380, 0.39830, 0.27130],
    [0.32840, 0.35420, 0.29380],
    [0.33720, 0.30970, 0.31230],
    [0.34340, 0.25860, 0.33170],
    [0.35430, 0.21470, 0.35250],
    [0.38640, 0.17860, 0.38420],
    [0.44430, 0.15200, 0.42810],
    [0.51270, 0.12830, 0.47810],
    [0.58180, 0.11030, 0.53670],
    [0.63050, 0.11630, 0.58990],
    [0.67300, 0.13600, 0.64400],
    [0.71430, 0.15850, 0.69900],
    [0.76110, 0.18370, 0.76180],
    [0.80290, 0.20620, 0.81850],
    [0.84510, 0.22870, 0.87590],
], dtype=np.float32)
_CBCHL_R = np.linspace(0.0, 255.0, len(_CBCHL_RGB))


# ---------------------------------------------------------------------------
# Prefix-to-canonical name map
# ---------------------------------------------------------------------------
_NAME_MAP: dict[str, str] = {
    'blu': 'blue',
    'gre': 'green',
    'div': 'diverging',
    'wat': 'water',
    'gla': 'gland',
    'lan': 'land',
    'bla': 'bland',
    'dep': 'depth',
    'odv': 'odv',
    '1cy': '1cyclic',
    'cyc': '1cyclic',   # 'cyclic' → 1cyclic by default
    '2cy': '2cyclic',
    'chl': 'chlorophyll',
    'ek8': 'EK80',
    'bod': 'BOD',
    'mbo': 'mBOD',
    'rbo': 'rBOD',
    'cbc': 'CBchlorophyll',
}


def _step_indices(m: int = 256, ncol: int = 16) -> np.ndarray:
    """Return a length-m array of colour-table positions in [0, 255] using the
    MATLAB m_colmap cosine-bunching algorithm.

    Multiple output entries map to the same input colour, creating ``ncol``
    perceptual bands with smooth intra-band gradients rather than hard steps.
    """
    xx = np.arange(m) / (m - 1) * np.pi * ncol
    yy = np.cumsum(np.cos(xx) ** 4 + 1.0 / 30.0)
    yy = yy - yy[0]
    yy = yy / yy[-1] * 255.0
    return yy


def m_colmap(name: str, n=64, ncol: int = 16) -> ListedColormap:
    """
    Return a ListedColormap for the named colormap.

    Parameters
    ----------
    name : str
        Colormap name (case-insensitive, prefix-matched).
        Built-in: 'blues'/'blue', 'gland'/'land', 'water', 'jet', plus any
        matplotlib colormap name as a fallback.
    n : int or 'step'
        If an integer, return that many uniformly-spaced colours (default 64).
        If ``'step'``, return 256 colours using the MATLAB cosine-bunching
        redistribution: colours are perceptually bunched into ``ncol`` bands
        (smooth gradients within each band) — visually similar to contouring.
    ncol : int
        Number of perceptual bands when ``n='step'`` (default 16).

    Returns
    -------
    matplotlib.colors.ListedColormap
    """
    step_mode = isinstance(n, str) and n.lower().startswith('ste')
    m = 256 if step_mode else int(n)

    key = name.lower()[:3]
    canonical = _NAME_MAP.get(key)

    if canonical is None:
        # Fall back to a matplotlib colormap of the same name
        try:
            import matplotlib as mpl
            cmap = mpl.colormaps.get_cmap(name.lower())
            if step_mode:
                yy = _step_indices(m, ncol) / 255.0
            else:
                yy = np.linspace(0.0, 1.0, m)
            return ListedColormap(cmap(yy)[:, :3].astype(np.float32))
        except (ValueError, KeyError):
            raise ValueError(
                f"Colormap '{name}' not found in m_colmap or matplotlib. "
                f"Built-in names: 'blues', 'green', 'diverging', 'gland', "
                f"'land', 'bland', 'water', 'depth'."
            )

    yy = _step_indices(m, ncol) if step_mode else np.linspace(0.0, 255.0, m)

    if canonical == 'blue':
        cmap = plt.cm.Blues_r
        t = yy / 255.0
        return ListedColormap(cmap(t)[:, :3].astype(np.float32))

    elif canonical == 'green':
        cols = np.column_stack([
            np.interp(yy, _GREEN_R, _GREEN_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'diverging':
        cols = np.column_stack([
            np.interp(yy, _DIV_R, _DIV_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'gland':
        cols = np.column_stack([
            np.interp(yy, _GLAND_R, _GLAND_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'land':
        cols = np.column_stack([
            np.interp(yy, _LAND_R, _GLAND_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'bland':
        cols = np.column_stack([
            np.interp(yy, _BLAND_R, _BLAND_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'water':
        cols = np.column_stack([
            np.interp(yy, _WATER_R, _WATER_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'depth':
        cols = np.column_stack([
            np.interp(yy, _DEPTH_R, _DEPTH_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'odv':
        cols = np.column_stack([
            np.interp(yy, _ODV_R, _ODV_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == '1cyclic':
        cols = np.column_stack([
            np.interp(yy, _CYCLIC1_R, _CYCLIC1_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == '2cyclic':
        cols = np.column_stack([
            np.interp(yy, _CYCLIC2_R, _CYCLIC2_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'chlorophyll':
        cols = np.column_stack([
            np.interp(yy, _CHLOROPHYLL_R, _CHLOROPHYLL_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'EK80':
        cols = np.column_stack([
            np.interp(yy, _EK80_R, _EK80_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'BOD':
        cols = np.column_stack([
            np.interp(yy, _BOD_R, _BOD_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'mBOD':
        cols = np.column_stack([
            np.interp(yy, _MBOD_R, _MBOD_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'rBOD':
        cols = np.column_stack([
            np.interp(yy, _RBOD_R, _RBOD_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    elif canonical == 'CBchlorophyll':
        cols = np.column_stack([
            np.interp(yy, _CBCHL_R, _CBCHL_RGB[:, c]) for c in range(3)
        ])
        return ListedColormap(cols.astype(np.float32))

    raise ValueError(f"Unknown canonical name: {canonical}")
