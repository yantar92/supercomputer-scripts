#!/usr/bin/env python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import argparse

# Parse command line arguments
parser = argparse.ArgumentParser(description='Plot max capacity from multiple functional sets')
parser.add_argument('data_sets', nargs='+', 
                    help='List of top-level directories containing subfolders for functionals')
parser.add_argument('ion', choices=['Li', 'Na'],
                    help='Ion type (Li or Na)')
parser.add_argument('--title', type=str, default='Max capacity',
                    help='Plot title (default: "Max capacity")')
parser.add_argument('--xlabel', type=str, default='d-spacing / Å',
                    help='Plot title (default: "d-spacing / Å")')
parser.add_argument('--labels', nargs='+',
                    help='Custom labels for optB88-vdW plots (one per data set)')
parser.add_argument('--output',
                    help='Output file name (default = max_capacity_multi.png',
                    default='max_capacity_multi.png')
args = parser.parse_args()

data_sets = args.data_sets
ion_type = args.ion
plot_title = args.title
custom_labels = args.labels if args.labels else None

functional_folders = {
    'optB88-vdW': '.',
    'optB86b-vdW': 'optB86b-vdW',
    'PBE+D2': 'PBE+D2',
    'vdW-DF': 'vdW-DF',
    'vdW-DF2': 'vdW-DF2',
}

def plot_voltage_range_for_set(set_dir, functional_folders, color, set_idx, plot_optb88=True):
    dfs = {}
    x_name = 'capacity' if plot_capacity else 'x'
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
            plt.step(df[x_name].values, df['voltage'].values, where='post', 
                    linewidth=1.5, linestyle='-', 
                    label=f'{set_dir} - {func_label}')
    else:
        if not plot_no_functionals:
            # Envelope across all functionals
            all_x = np.unique(np.concatenate([df[x_name].values for df in dfs.values()]))
            interp_voltages = {}
            for func_label, df in dfs.items():
                v_interp = np.interp(all_x, df[x_name].values, df['voltage'].values)
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
            plt.plot(df_optb[x_name].values, df_optb['voltage'].values,
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

data = {func_label: [] for func_label in functional_folders}
data['x_labels'] = args.labels
for set_dir, label in zip(data_sets, args.labels):
    for func_label, func_folder in functional_folders.items():
        filepath = Path(set_dir) / func_folder / 'voltage.out'
        if filepath.is_file():
            df = pd.read_csv(filepath, sep=' ')
            # find the largest df['capacity'] where df['voltage'] is positive
            max_capacity = df.loc[df['voltage'] > 0, 'capacity'].max()
            if pd.isna(max_capacity):
                max_capacity = 0
            data[func_label].append(max_capacity)
        else:
            print(f"Warning: {filepath} not found, skipping.")

df = pd.DataFrame(data).set_index('x_labels')
print(df)

x = np.arange(len(df))
total_width_fraction = 0.7 # fraction of max width to be occupied by all bars for single x
width = total_width_fraction*1.0/len(df.columns)  # width of each bar
colors = plt.get_cmap('tab10').colors
for i, column in enumerate(df.columns):

    positions = x + i * width
    color = colors[i]
    plt.bar(positions, df[column], width=width, label=column, color=color)

    # To prevent the line thickness from falling below y=0, we plot the indicator
    # at a small positive height (1.0), which is visually identical to the
    # baseline given the scale of the y-axis.
    indicator_height = 1.0
    
    # Build coordinates for the horizontal line segments. NaN is used to draw
    # disconnected segments in a single, efficient plot call.
    x_segments = []
    for pos in positions:
        x_segments.extend([pos - width / 2, pos + width / 2, np.nan])
    
    if x_segments: # Only plot if there are zero values
        y_segments = np.full_like(x_segments, indicator_height)
        plt.plot(x_segments, y_segments,
                 color=color,
                 linewidth=1.5,
                 solid_capstyle='butt', # Use flat line endings to match bar shape
                 label='_nolegend_')

plt.xticks(x + width*(len(df.columns)-1)/2, df.index)

plt.ylim(-10, 670)

# Add horizontal line at y=364.3903975181398
# The line should have annotation label "graphite"
plt.axhline(y=364.3903975181398, color='black', linestyle='--', linewidth=0.7)
plt.text(x[-1], 364.3903975181398 + 15, 'graphite', color='black', ha='right', va='bottom', fontsize=base_sz)

plt.xlabel(args.xlabel)
plt.ylabel('Max capacity / mAh/g')
plt.title(plot_title, pad=20)
plt.legend()
plt.tight_layout()
output_filename = args.output
plt.savefig(output_filename, dpi=600, bbox_inches='tight')
plt.savefig(output_filename + '.svg', dpi=600, bbox_inches='tight')
