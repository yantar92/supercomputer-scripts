#!/usr/bin/env python3
"""
Plot formation‑energy histories from mc‑pore.py snapshots.

Usage:
    python plot_formation_energy.py [--voltage 0] [--output-dir ./plots] [--prefix formation]

Produces two families of PNGs in OUTPUT_DIR:
1. fixed defect‑probability and temperature, varied radius:
       {PREFIX}_V{voltage}_P{defect_probability}_T{temperature}.png
2. fixed defect‑probability and radius, varied temperature:
       {PREFIX}_V{voltage}_P{defect_probability}_R{radius}.png
"""

import glob
import pickle
import re
import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
from alive_progress import alive_it

# Use non‑interactive backend for batch saving
plt.switch_backend('Agg')

class HardCarbonPoreModel:
    pass

def parse_filename(fname):
    """
    Extract (voltage, defect_probability, temperature, radius, index)
    from a filename like '0.100_0.000_1500_15_0.pkl'.
    Returns a tuple of floats/ints, or None if the pattern does not match.
    """
    basename = os.path.basename(fname)
    # Remove extension
    basename = basename.replace('.pkl', '')
    parts = basename.split('_')
    if len(parts) != 5:
        return None
    try:
        voltage = float(parts[0])
        defect = float(parts[1])
        temp = float(parts[2])
        radius = float(parts[3])
        index = int(parts[4])
        return voltage, defect, temp, radius, index
    except ValueError:
        return None


def load_snapshot_data(filepath):
    """
    Load the pickle file, take the last snapshot, and extract
    time_points and formation_energy_history.
    Returns (time_points, formation_energy) or (None, None) on error.
    """
    try:
        with open(filepath, 'rb') as f:
            snapshots = pickle.load(f)
        if not snapshots:
            print(f"Warning: {filepath} contains no snapshots")
            return None, None
        model = snapshots[-1]
        time = model.time_points
        energy = model.formation_energy_history
        # Sanity check: lengths must match
        if len(time) != len(energy):
            print(f"Warning: length mismatch in {filepath}")
            return None, None
        del model
        del snapshots
        return time, energy
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None, None


def plot_multiple_curves(curve_dict, xlabel='Monte Carlo Steps',
                         ylabel='Formation energy (eV/atom)',
                         title=None, outfile=None):
    """
    Plot several curves on a single figure.
    curve_dict: dict {label: list_of_curves}, where each curve is (x, y).
    If a label has multiple curves (replicates), they are plotted with alpha=0.5.
    """
    fig, ax = plt.subplots(figsize=(8, 5))
    for label, curves in curve_dict.items():
        if not curves:
            continue
        # If only one curve, plot with solid line
        if len(curves) == 1:
            x, y = curves[0]
            ax.plot(x, y, label=label, linewidth=1.5)
        else:
            # Multiple replicates: plot each with transparency
            for i, (x, y) in enumerate(curves):
                ax.plot(x, y, label=label if i == 0 else None,
                        alpha=0.5, linewidth=1.0)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if title:
        ax.set_title(title)
    ax.legend(fontsize='small')
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    if outfile:
        fig.savefig(outfile, dpi=150)
        print(f"Saved {outfile}")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--voltage', type=float, default=0.0,
                        help='Voltage to filter (default 0)')
    parser.add_argument('--output-dir', type=str, default='./plots',
                        help='Directory for output PNGs (default ./plots)')
    parser.add_argument('--prefix', type=str, default='formation',
                        help='Prefix for output filenames (default "formation")')
    args = parser.parse_args()

    # Find all .pkl files in the current directory
    pkl_files = glob.glob('*.pkl')
    if not pkl_files:
        print("No .pkl files found in current directory.")
        return

    # Parse filenames and collect data
    data = {}  # key: (voltage, defect, temp, radius, index) -> (time, energy)
    for f in alive_it(pkl_files, title="Reading .pkl files"):
        params = parse_filename(f)
        if params is None:
            print(f"Skipping unrecognized filename: {f}")
            continue
        v, d, t, r, idx = params
        if v != args.voltage:
            continue  # keep only the requested voltage
        time, energy = load_snapshot_data(f)
        if time is None:
            continue
        data[(v, d, t, r, idx)] = (time, energy)

    if not data:
        print(f"No data found for voltage = {args.voltage}")
        return

    # Create output directory if needed
    os.makedirs(args.output_dir, exist_ok=True)

    # Extract unique defect probabilities, temperatures, radii
    defects = sorted({d for (_, d, _, _, _) in data})
    temps = sorted({t for (_, _, t, _, _) in data})
    radii = sorted({r for (_, _, _, r, _) in data})

    print(f"Found {len(data)} datasets")
    print(f"Defect probabilities: {defects}")
    print(f"Temperatures: {temps}")
    print(f"Radii: {radii}")

    # ------------------------------------------------------------------
    # 1. For each (defect, temperature) plot curves for different radii
    # ------------------------------------------------------------------
    for d in defects:
        for t in temps:
            # Gather curves for this (d,t) across all radii and indices
            curves_by_radius = {}
            for (v, d2, t2, r, idx), (time, energy) in data.items():
                if d2 != d or t2 != t:
                    continue
                label = f"R={r} Å"
                if label not in curves_by_radius:
                    curves_by_radius[label] = []
                curves_by_radius[label].append((time, energy))

            if not curves_by_radius:
                continue

            # Create plot
            title = (f"Voltage = {args.voltage} V, "
                     f"Defect = {d}, T = {t} K")
            outname = (f"{args.prefix}_T{t}_V{args.voltage}_P{d}.png")
            outpath = os.path.join(args.output_dir, outname)
            plot_multiple_curves(curves_by_radius,
                                 title=title,
                                 outfile=outpath)

    # ------------------------------------------------------------------
    # 2. For each (defect, radius) plot curves for different temperatures
    # ------------------------------------------------------------------
    for d in defects:
        for r in radii:
            curves_by_temp = {}
            for (v, d2, t, r2, idx), (time, energy) in data.items():
                if d2 != d or r2 != r:
                    continue
                label = f"T={t} K"
                if label not in curves_by_temp:
                    curves_by_temp[label] = []
                curves_by_temp[label].append((time, energy))

            if not curves_by_temp:
                continue

            title = (f"Voltage = {args.voltage} V, "
                     f"Defect = {d}, R = {r} Å")
            outname = (f"{args.prefix}_R{r}_V{args.voltage}_P{d}.png")
            outpath = os.path.join(args.output_dir, outname)
            plot_multiple_curves(curves_by_temp,
                                 title=title,
                                 outfile=outpath)

    print("\nAll plots saved to", args.output_dir)


if __name__ == '__main__':
    main()
