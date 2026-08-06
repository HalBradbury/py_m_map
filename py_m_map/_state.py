"""
Global map state singleton, replacing MATLAB's MAP_PROJECTION / MAP_VAR_LIST globals.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Tuple
import numpy as np


@dataclass
class MapState:
    projection_name: Optional[str] = None
    lon_limits: Optional[Tuple[float, float]] = None
    lat_limits: Optional[Tuple[float, float]] = None
    proj: object = None          # pyproj.Proj instance
    x_limits: Optional[Tuple[float, float]] = None
    y_limits: Optional[Tuple[float, float]] = None
    ellipsoid: str = 'normal'    # 'normal' = sphere r=6370997 m
    projection_type: str = 'rectangular'  # 'rectangular' | 'circular' | 'conic'
    center_lat: float = 0.0      # projection centre latitude  (circular only)
    center_lon: float = 0.0      # projection centre longitude (circular only)
    x_offset: float = 0.0        # absolute x-shift for interrupted pseudocylindrical lobes
    # For oblique projections: wider geographic limits used only for coast polygon
    # pre-filtering (coast clips in projected space; lon/lat limits are for ticks).
    coast_lon_limits: Optional[Tuple[float, float]] = None
    coast_lat_limits: Optional[Tuple[float, float]] = None
    # UTM-specific fields
    utm_zone: Optional[int] = None
    utm_south: bool = False
    # Title y position in axes coordinates — set by m_grid when box='fancy'
    # so that titles clear the outer ruler border regardless of figure size.
    title_y: Optional[float] = None


_state = MapState()


def get_state() -> MapState:
    return _state


def reset_state() -> None:
    global _state
    _state = MapState()
