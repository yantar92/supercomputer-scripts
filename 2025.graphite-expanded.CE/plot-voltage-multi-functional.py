#!/usr/bin/env python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

folders = {
    '.': 'optB88-vdW',
    'optB86b-vdW': 'optB86b-vdW',
    'PBE+D2': 'PBE+D2',
    'vdW-DF': 'vdW-DF',
    'vdW-DF2': 'vdW-DF2',
}

dfs = {}
for folder, label in folders.items():
    filepath = Path(folder) / 'voltage.out'
    if filepath.is_file():
        df = pd.read_csv(filepath, sep = ' ')
        dfs[label] = df
    else:
        print(f"Warning: {filepath} not found, skipping.")

all_x = np.unique(np.concatenate([df['x'].values for df in dfs.values()]))

interp_voltages = {}
for label, df in dfs.items():
    v_interp = np.interp(all_x, df['x'], df['voltage'])
    interp_voltages[label] = v_interp

stacked = np.column_stack([v for v in interp_voltages.values()])
voltage_min = np.min(stacked, axis=1)
voltage_max = np.max(stacked, axis=1)

# For step plots, duplicate each x except the last, so steps are correct
def step_data(x, y):
    x_step = np.repeat(x, 2)[1:]
    y_step = np.repeat(y, 2)[:-1]
    return x_step, y_step

x_step, min_step = step_data(all_x, voltage_min)
_, max_step = step_data(all_x, voltage_max)

plt.figure(figsize=(10, 6))
plt.fill_between(x_step, min_step, max_step, step='pre', color='lightblue', alpha=0.5, label='Voltage Range (All functionals)')
plt.step(all_x, voltage_min, where='post', color='blue', linewidth=1, linestyle='--', label='Min voltage')
plt.step(all_x, voltage_max, where='post', color='blue', linewidth=1, linestyle='--', label='Max voltage')
plt.axhline(y=0)

for name in interp_voltages:
    plt.step(all_x, interp_voltages[name], where='post', label=name, linewidth=2)
# if 'optB86b-vdW' in interp_voltages:
#     plt.step(all_x, interp_voltages['optB86b-vdW'], where='post', label='optB86b-vdW', color='black', linewidth=2)

plt.xlabel('Concentration (x)')
plt.ylabel('Voltage (V)')
plt.title('Voltage Profile Range from Different Functionals')
plt.legend()
plt.tight_layout()
plt.savefig('voltage_range.png', dpi=300)
plt.show()
