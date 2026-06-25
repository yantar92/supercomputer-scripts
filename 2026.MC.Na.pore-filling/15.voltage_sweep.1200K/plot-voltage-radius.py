import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from pathlib import Path

TEMPERATURE = 1200
DEFECT_CONCENTRATION = 0


# --- Publication style (good for ~half A4 width figure) ---
a4_width = 4.13 * 2
width = a4_width / 2
height = width * 3 / 4
# height = width * 2 / 4 * 0.75
mpl.rcParams.update({
    # "figure.figsize": (4.13, 3.10),   # half A4 width, 4:3 ratio
    "figure.figsize": (width, height),
    "figure.dpi": 300,
    "savefig.dpi": 600,

    "font.size": 13,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "legend.fontsize": 11,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,

    "axes.linewidth": 0.8,
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "xtick.minor.width": 0.6,
    "ytick.minor.width": 0.6,

    "lines.linewidth": 1.5,
    "lines.markersize": 4.2,

    "pdf.fonttype": 42,   # editable text in Illustrator
    "ps.fonttype": 42,
    "mathtext.default": "regular",
})


df = pd.read_csv(
    'results.csv',
    names=[
        "voltage", "radius",
        "defect_probability", "defect_placement",
        "energy_na_defect", "energy_na_na", "energy_na_c",
        "temperature", "steps", "seed",
        "final_filling", "equilibrium_reached", "mcs",
        "n_valid_sites", "n_surface_sites", "default_p_gcmc",
        "mu", "fill_mcs"
    ],
)

# fig, (ax1, ax2) = plt.subplots(1, 2, width_ratios=[1, 1], sharey=True)
fig, ax = plt.subplots()
fig.subplots_adjust(wspace=0.05)  # adjust space between Axes

# This is limiting to calculations where we sample over fixed pore defect distribution
df = df[np.isclose(df['temperature'], TEMPERATURE)]
df = df[np.isclose(df['defect_probability'], DEFECT_CONCENTRATION)]
radii = df['radius'].unique()
# sel = np.r_[radii[radii < 10.0], radii[radii >= 10.0][::2]]
# sel = [5, 7, 8, 11, 20, 30]
sel = sorted(radii)

# df = df[np.isclose(df["final_filling"], 100)]
df = df.dropna(subset=['fill_mcs'])

data = {'radius': [], 'voltage': [], 'voltage_q1': [], 'voltage_q3': []}

seen_n_valid = []

for r in sel:
    tem = df[np.isclose(df["radius"], r)]
    assert tem['n_valid_sites'].max() == tem['n_valid_sites'].min()
    n_valid = tem['n_valid_sites'].max()
    seen = False
    for n in seen_n_valid:
        if np.isclose(n_valid, n):
            seen = True
            break
    if seen:
        print(f"Skipping r={r}")
        continue
    seen_n_valid.append(n_valid)
    tem['voltage'] = pd.to_numeric(tem['voltage'])
    data['radius'].append(r)
    data['voltage'].append(tem['voltage'].median())
    data['voltage_q1'].append(tem['voltage'].quantile(0.25))
    data['voltage_q3'].append(tem['voltage'].quantile(0.75))


ax.errorbar(
    2*np.array(data['radius'])/10, data['voltage'],
    yerr=[np.array(data['voltage']) - np.array(data['voltage_q1']),
          np.array(data['voltage_q3']) - np.array(data['voltage'])],
    fmt="o",
    color='black',
    markerfacecolor="black",
    markeredgewidth=0.8,
    elinewidth=0.5
)
# ax.fill_between(2*np.array(data['radius'])/10,
#                 data['voltage_q1'], data["voltage_q3"],
#                 alpha=0.2, linewidth=0, color='black')

diameters = 2 * np.array(data['radius']) / 10
voltages = np.array(data['voltage'])
A, B = np.polyfit(1/diameters, voltages, 1)
x = np.linspace(min(diameters), max(diameters), 100)
ax.plot(x, A/x + B, color='black', linewidth=1, linestyle='-',
        label=f'V = {A:.2f}/d')

# ax.plot(x, A/x + B, color='black', linewidth=1, linestyle='-',
#         label=f'V = {A:.2f}/d {'-' if B<0 else '+'} {np.abs(B):.2f}')

ax.set_xlabel("Diameter (nm)")
ax.set_ylabel("Filling voltage (V)")
# ax.set_xlim(-0.5, 101)
# ax.set_ylim(0, 1.5)
ax.legend()

fig.savefig(f"Figure4c.svg", bbox_inches="tight")
fig.savefig(f"Figure4c.png", bbox_inches="tight")
plt.show()

