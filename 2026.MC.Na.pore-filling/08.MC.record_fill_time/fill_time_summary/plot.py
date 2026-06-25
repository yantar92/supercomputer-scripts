"""
Process CSV output from mc‑pore.py and plot filling time (mcs_fill) vs temperature.

Assumptions:
- CSV files are named resultsT*.csv (e.g., resultsT1300.csv) and reside in the same directory.
- Each CSV has the columns produced by mc‑pore.py's --csv output:
    voltage, radius, defect_probability, defect_placement,
    energy_na_defect, energy_na_na, energy_na_c, temp, steps, seed,
    final_filling, equilibrium_reached, mcs, n_valid_sites,
    n_surface_sites, default_p_gcmc, mu, mcs_fill
- mcs_fill may be empty (NaN) if the pore never reached 100% filling during the simulation.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
import os
import sys

def load_all_data(pattern='resultsT*.csv', data_dir='.'):
    """
    Read all CSV files matching PATTERN in DATA_DIR and concatenate them.
    """
    files = sorted(glob.glob(os.path.join(data_dir, pattern)))
    if not files:
        print(f"No files matching {pattern} in {data_dir}")
        sys.exit(1)
    
    dfs = []
    for f in files:
        print(f"Reading {f}...")
        # Use low_memory=False to avoid dtype warnings; mcs_fill may be mixed type
        df = pd.read_csv(f, low_memory=False,
                         names=[
                             "voltage", "radius",
                             "defect_probability", "defect_placement",
                             "energy_na_defect", "energy_na_na", "energy_na_c",
                             "temp", "steps", "seed",
                             "final_filling", "equilibrium_reached", "mcs",
                             "n_valid_sites", "n_surface_sites", "default_p_gcmc",
                             "mu", "mcs_fill"
                         ]
                         )
        # Ensure numeric columns are numeric (coerce errors to NaN)
        numeric_cols = ['voltage', 'radius', 'defect_probability',
                        'energy_na_defect', 'energy_na_na', 'energy_na_c',
                        'temp', 'steps', 'final_filling', 'mcs',
                        'n_valid_sites', 'n_surface_sites', 'default_p_gcmc',
                        'mu', 'mcs_fill']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        dfs.append(df)
    
    combined = pd.concat(dfs, ignore_index=True)
    print(f"Loaded {len(combined)} rows from {len(files)} files.")
    return combined

def create_individual_plots(df, output_dir='plots'):
    """
    For each unique (voltage, radius) pair, create a plot of mcs_fill vs temperature.
    Points are colored by defect_probability (if it varies).
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Group by voltage and radius
    grouped = df.groupby(['voltage', 'radius'])
    
    for (voltage, radius), group in grouped:
        # Drop rows where mcs_fill is NaN (pore never filled)
        group = group.dropna(subset=['mcs_fill'])
        if group.empty:
            print(f"Warning: No filling data for V={voltage}, R={radius}")
            continue
        
        # Determine if defect_probability varies within this group
        n_defect_vals = group['defect_probability'].nunique()
        
        fig, ax = plt.subplots(figsize=(8, 6))
        
        if n_defect_vals > 1:
            # Scatter with color mapping for defect probability
            sc = ax.scatter(group['temp'], group['mcs_fill'],
                           c=group['defect_probability'],
                           cmap='viridis', alpha=0.7, edgecolors='k', linewidths=0.5)
            cbar = plt.colorbar(sc, ax=ax)
            cbar.set_label('Defect probability')
        else:
            # Single defect probability: simple scatter
            ax.scatter(group['temp'], group['mcs_fill'],
                       alpha=0.7, edgecolors='k', linewidths=0.5)
        
        ax.set_xlabel('Temperature (K)')
        ax.set_ylabel('Filling time (MCS)')
        title = f'Pore filling time vs temperature\nVoltage = {voltage:.3f} V, Radius = {radius:.1f} Å'
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        
        # Optional: add a simple fit line (log scale often needed)
        if len(group) >= 3:
            # Try to show trend on log scale if mcs_fill spans orders of magnitude
            if group['mcs_fill'].max() / group['mcs_fill'].min() > 10:
                ax.set_yscale('log')
        
        # Save figure
        safe_voltage = f'{voltage:.3f}'.replace('.', 'p')
        safe_radius = f'{radius:.1f}'.replace('.', 'p')
        fname = os.path.join(output_dir, f'filltime_v{safe_voltage}_r{safe_radius}.png')
        plt.tight_layout()
        plt.savefig(fname, dpi=150)
        plt.close()
        print(f"Saved {fname}")

def create_summary_plot(df, output_dir='plots'):
    """
    Create a single overview plot with multiple curves (one per unique radius and voltage).
    Each curve is the median mcs_fill vs temperature for that (voltage, radius) group.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Group by voltage, radius, and temperature, compute median filling time
    # (ignore defect probability for this summary)
    summary = df.groupby(['voltage', 'radius', 'temp'])['mcs_fill'].median().reset_index()
    summary = summary.dropna()
    
    if summary.empty:
        print("No filling data for summary plot.")
        return
    
    # Create a color map for radii and line styles for voltages
    radii = sorted(summary['radius'].unique())
    voltages = sorted(summary['voltage'].unique())
    
    # Choose a colormap for radii
    cmap = plt.cm.get_cmap('tab10', len(radii))
    
    fig, ax = plt.subplots(figsize=(10, 7))
    
    for i, radius in enumerate(radii):
        for voltage in voltages:
            sub = summary[(summary['radius'] == radius) & (summary['voltage'] == voltage)]
            if len(sub) < 2:
                continue
            # Sort by temperature for line plot
            sub = sub.sort_values('temp')
            line, = ax.plot(sub['temp'], sub['mcs_fill'],
                           color=cmap(i),
                           linestyle='-' if voltage == voltages[0] else '--',
                           linewidth=2,
                           label=f'R={radius} Å, V={voltage:.3f} V')
    
    ax.set_xlabel('Temperature (K)')
    ax.set_ylabel('Median filling time (MCS)')
    ax.set_title('Pore filling time vs temperature (median across defect probabilities)')
    ax.grid(True, alpha=0.3)
    
    # Use log scale if data spans orders of magnitude
    if summary['mcs_fill'].max() / summary['mcs_fill'].min() > 10:
        ax.set_yscale('log')
    
    # Place legend outside
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
    
    plt.tight_layout()
    fname = os.path.join(output_dir, 'summary_filltime_vs_temperature.png')
    plt.savefig(fname, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved summary plot {fname}")

def main():
    # Adjust the path to the directory containing the CSV files
    data_dir = '.'   # change if needed
    output_dir = 'plots'
    
    df = load_all_data(pattern='resultsT*.csv', data_dir=data_dir)
    
    # Check that required columns exist
    required = ['voltage', 'radius', 'temp', 'mcs_fill']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Missing columns: {missing}")
        print("Available columns:", df.columns.tolist())
        sys.exit(1)
    
    # Create individual plots for each (voltage, radius) pair
    create_individual_plots(df, output_dir)
    
    # Create a summary plot
    create_summary_plot(df, output_dir)
    
    print("All plots generated in", output_dir)

if __name__ == '__main__':
    main()
