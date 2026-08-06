"""
Example 4 — Two Interrupted Projections of the World's Oceans.

Run directly:

    python tests/test_example4.py

Output saved to tests/outputs/example4.png.

Python equivalent of the MATLAB code (from map.html, Example 4):

    subplot(211);
    Slongs=[-100 0;-75 25;0 45; 25 145;45 100;145 295;100 295];
    Slats= [   8 80;-80  8;  8  80;-80   8; 8   80;-80   0; 0 80];
    for l=1:7
        m_proj('sinusoidal','long',Slongs(l,:),'lat',Slats(l,:));
        m_grid('fontsize',6,'xticklabels',[],'xtick',[-180:30:360],...
                    'ytick',[-80:20:80],'yticklabels',[],'linest','-','color',[.7 .7 .7]);
        m_coast('patch','g');
    end
    xlabel('Interrupted Sinusoidal Projection of World Oceans');
    set(gca,'xlimmode','auto','ylimmode','auto');

    subplot(212);
    Slongs=[-100 43;-75 20; 20 145;43 100;145 295;100 295];
    Slats= [  0  90;-90  0;-90   0; 0  90;-90   0;  0  90];
    for l=1:6
        m_proj('mollweide','long',Slongs(l,:),'lat',Slats(l,:));
        m_grid('fontsize',6,'xticklabels',[],'xtick',[-180:30:360],...
                    'ytick',[-80:20:80],'yticklabels',[],'linest','-','color','k')
        m_coast('patch',[.6 .6 .6]);
    end
    xlabel('Interrupted Mollweide Projection of World Oceans');
    set(gca,'xlimmode','auto','ylimmode','auto');

Notes
-----
* Each lobe is a separate m_proj call; all lobes share the same axes.
* After the loop, ax.relim() / autoscale_view() replaces MATLAB's
  set(gca,'xlimmode','auto','ylimmode','auto').
* Pacific lobes like [145, 295] cross the antimeridian — coast.py handles
  this by splitting the clip box and wrapping coordinates.
"""
from __future__ import annotations
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)
if _PKG_ROOT not in sys.path:
    sys.path.insert(0, _PKG_ROOT)

from py_m_map import m_proj, m_grid, m_coast, reset_state


def run_example4(out_path: str = 'outputs/example4.png'):
    """Reproduce Example 4 and save to out_path."""
    reset_state()

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Tick arrays match MATLAB's [-180:30:360] and [-80:20:80]
    lon_ticks = np.arange(-180, 361, 30, dtype=float)
    lat_ticks = np.arange(-80, 81, 20, dtype=float)

    # -----------------------------------------------------------------------
    # Subplot 1: Interrupted Sinusoidal Projection
    # -----------------------------------------------------------------------
    plt.sca(axes[0])

    slongs = [
        [-100,   0],
        [ -75,  25],
        [   0,  45],
        [  25, 145],
        [  45, 100],
        [ 145, 295],
        [ 100, 295],
    ]
    slats = [
        [  8,  80],
        [-80,   8],
        [  8,  80],
        [-80,   8],
        [  8,  80],
        [-80,   0],
        [  0,  80],
    ]

    for lons, lats in zip(slongs, slats):
        m_proj('sinusoidal', lon=lons, lat=lats)
        m_grid(
            fontsize=6,
            xticklabels=[],
            xtick=lon_ticks,
            ytick=lat_ticks,
            yticklabels=[],
            linest='-',
            color=[0.7, 0.7, 0.7],
        )
        m_coast('patch', 'g')

    axes[0].relim()
    axes[0].autoscale_view()
    axes[0].set_xlabel('Interrupted Sinusoidal Projection of World Oceans')

    # -----------------------------------------------------------------------
    # Subplot 2: Interrupted Mollweide Projection
    # -----------------------------------------------------------------------
    plt.sca(axes[1])

    mlongs = [
        [-100,  43],
        [ -75,  20],
        [  20, 145],
        [  43, 100],
        [ 145, 295],
        [ 100, 295],
    ]
    mlats = [
        [  0,  90],
        [-90,   0],
        [-90,   0],
        [  0,  90],
        [-90,   0],
        [  0,  90],
    ]

    for lons, lats in zip(mlongs, mlats):
        m_proj('mollweide', lon=lons, lat=lats)
        m_grid(
            fontsize=6,
            xticklabels=[],
            xtick=lon_ticks,
            ytick=lat_ticks,
            yticklabels=[],
            linest='-',
            color='k',
        )
        m_coast('patch', [0.6, 0.6, 0.6])

    axes[1].relim()
    axes[1].autoscale_view()
    axes[1].set_xlabel('Interrupted Mollweide Projection of World Oceans')

    plt.tight_layout()
    os.makedirs(
        os.path.dirname(out_path) if os.path.dirname(out_path) else '.',
        exist_ok=True,
    )
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved: {out_path}")


def test_example4():
    out = os.path.join(_HERE, 'outputs', 'example4.png')
    os.makedirs(os.path.join(_HERE, 'outputs'), exist_ok=True)
    run_example4(out)


if __name__ == '__main__':
    out = os.path.join(_HERE, 'outputs', 'example4.png')
    run_example4(out)
