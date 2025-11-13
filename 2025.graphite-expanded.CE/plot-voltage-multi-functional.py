#!/usr/bin/env python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot voltage profiles from multiple functional sets')
parser.add_argument('data_sets', nargs='+', 
                   help='List of top-level directories containing subfolders for functionals')
parser.add_argument('ion', choices=['Li', 'Na'],
                   help='Ion type (Li or Na)')
parser.add_argument('--title', type=str, default='Voltage profile',
                   help='Plot title (default: "Voltage profile")')
parser.add_argument('--labels', nargs='+', 
                   help='Custom labels for optB88-vdW plots (one per data set)')
parser.add_argument('--xmax', type=float, 
                   help='Maximum concentration to plot (x-axis limit)')
parser.add_argument('--ymin', type=float, 
                   help='Min voltage to plot (y-axis limit)')
parser.add_argument('--ymax', type=float, 
                   help='Max voltage to plot (y-axis limit)')
parser.add_argument('--plot_all_functionals', action='store_true',
                   help='Plot all functionals individually as step plots with functional labels')
parser.add_argument('--plot_no_functionals', action='store_true',
                    help='Do not plot multiple functionals')
args = parser.parse_args()

data_sets = args.data_sets
ion_type = args.ion
plot_title = args.title
custom_labels = args.labels if args.labels else None
xmax = args.xmax
ymin = args.ymin
ymax = args.ymax
plot_all_functionals = args.plot_all_functionals
plot_no_functionals = args.plot_no_functionals

functional_folders = {
    'optB88-vdW': '.',
    'optB86b-vdW': 'optB86b-vdW',
    'PBE+D2': 'PBE+D2',
    'vdW-DF': 'vdW-DF',
    'vdW-DF2': 'vdW-DF2',
}

def plot_voltage_range_for_set(set_dir, functional_folders, color, set_idx, plot_optb88=True):
    dfs = {}
    for func_label, func_folder in functional_folders.items():
        filepath = Path(set_dir) / func_folder / 'voltage.out'
        if filepath.is_file():
            df = pd.read_csv(filepath, sep=' ')
            # In voltage.out, we use LiC2 -> concentration = 0.5 convention
            # Transfer to pymatgen's PhaseDiagram LiC2 -> concentration = 1/3 convention
            df['x'] = df['x']/(df['x'] + 1)
            dfs[func_label] = df
        else:
            print(f"Warning: {filepath} not found, skipping.")

    if not dfs:
        print(f"Warning: No voltage.out files found for {set_dir}")
        return

    # Plot individual functionals if flag is set
    if plot_all_functionals and not plot_no_functionals:
        for func_label, df in dfs.items():
            plt.step(df['x'].values, df['voltage'].values, where='post', 
                    linewidth=1.5, linestyle='-', 
                    label=f'{set_dir} - {func_label}')
    else:
        if not plot_no_functionals:
            # Envelope across all functionals
            all_x = np.unique(np.concatenate([df['x'].values for df in dfs.values()]))
            interp_voltages = {}
            for func_label, df in dfs.items():
                v_interp = np.interp(all_x, df['x'].values, df['voltage'].values)
                interp_voltages[func_label] = v_interp

            stacked = np.column_stack(list(interp_voltages.values()))
            voltage_min = np.min(stacked, axis=1)
            voltage_max = np.max(stacked, axis=1)

            def step_data(x, y):
                x_step = np.repeat(x, 2)[1:]
                y_step = np.repeat(y, 2)[:-1]
                return x_step, y_step

            x_step, min_step = step_data(all_x, voltage_min)
            _, max_step = step_data(all_x, voltage_max)

            # Plot shaded area without label
            plt.fill_between(
                x_step, min_step, max_step, step='pre',
                color=color, alpha=0.35
            )
            # Plot area boundaries without labels
            # plt.step(all_x, voltage_min, where='post', color=color, linewidth=1, linestyle='--')
            # plt.step(all_x, voltage_max, where='post', color=color, linewidth=1, linestyle='--')

        # Plot optB88-vdW as solid line with custom label
        if plot_optb88 and 'optB88-vdW' in dfs:
            df_optb = dfs['optB88-vdW']
            if custom_labels and set_idx < len(custom_labels):
                label = custom_labels[set_idx]
            else:
                label = set_dir
            plt.plot(df_optb['x'].values, df_optb['voltage'].values,
                    color=color, linewidth=2, label=label)

# Set publication-quality style matching atat-formation-energies.py
plt.style.use('default')
base_sz = 8
plt.rcParams.update({
    'font.size': base_sz,
    'font.family': 'serif',
    'font.serif': ['Times New Roman', 'DejaVu Serif'],
    'mathtext.fontset': 'stix',
    'axes.labelsize': base_sz,
    'axes.titlesize': base_sz * 1.2,
    'axes.linewidth': 1.0,
    'lines.linewidth': 1.2,
    'lines.markersize': base_sz * 0.5,
    'xtick.labelsize': base_sz,
    'ytick.labelsize': base_sz,
    'legend.fontsize': base_sz,
    'figure.titlesize': base_sz * 1.2,
})

# Create figure with same aspect ratio as atat-formation-energies.py
plt.figure(figsize=(4.13, 3))  # half A4, matching the formation energy plot

colors = plt.rcParams['axes.prop_cycle'].by_key()['color']
for i, set_dir in enumerate(data_sets):
    fill_color = colors[i % len(colors)]
    plot_voltage_range_for_set(set_dir, functional_folders, fill_color, i, plot_optb88=not plot_all_functionals)

plt.ylim(ymin, ymax)

plt.axhline(y=0, color='black', linewidth=0.8, linestyle=':')
# Add vertical line for IonC6 concentration
ionc6_concentration = 1/7
plt.axvline(x=ionc6_concentration, color='red', linewidth=1, linestyle='--', alpha=0.7)
# Add annotation for IonC6
plt.annotate(f'{ion_type}C$_{6}$', xy=(ionc6_concentration, plt.ylim()[1]*0.95), 
             xytext=(ionc6_concentration+0.02, plt.ylim()[1]*0.95),
             ha='left', va='top', fontsize=base_sz,
             arrowprops=dict(arrowstyle='->', color='red', alpha=0.7, lw=0.8))
plt.xlabel(f'{ion_type} concentration')
plt.ylabel(fr'Voltage vs {ion_type}/{ion_type}$^+$ / V')
plt.gca().xaxis.set_major_formatter(plt.FormatStrFormatter('%.2f'))
plt.title(plot_title, pad=20)
plt.legend()
plt.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)
if xmax is not None:
    plt.xlim(0, xmax)
plt.tight_layout()
output_filename = f'{ion_type.lower()}_voltage_range_multi_with_optB88.png'
if plot_all_functionals:
    output_filename = f'{ion_type.lower()}_voltage_all_functionals.png'
plt.savefig(output_filename, dpi=600, bbox_inches='tight', 
            facecolor='white', edgecolor='none')
plt.show()
