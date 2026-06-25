import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from pathlib import Path
import sys

sys.path.insert(0, "../mc-pore")
from mcpore import HardCarbonPoreModel


TEMPERATURE = 1200
DEFECT_CONCENTRATION = 0


# --- Publication style (good for ~half A4 width figure) ---
a4_width = 4.13 * 2
width = a4_width * 1.12
# height = width * 3 / 4
height = width * 2 / 4 * 0.75
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

cmap = mpl.colormaps["tab10"]

# This is limiting to calculations where we sample over fixed pore defect distribution
df = df[np.isclose(df['temperature'], TEMPERATURE)]
df = df[np.isclose(df['defect_probability'], DEFECT_CONCENTRATION)]
radii = df['radius'].unique()
# sel = np.r_[radii[radii < 10.0], radii[radii >= 10.0][::2]]
# sel = [5, 7, 8, 11, 20, 30]
sel = [5, 8, 20, 30]

for r, color in zip(sel, cmap.colors):
    tem = df[np.isclose(df["radius"], r)]
    print(tem['voltage'])
    tem['voltage'] = pd.to_numeric(tem['voltage'])
    g = tem.groupby("voltage")["final_filling"]
    avg = g.median()
    avg_min = g.min()
    avg_max = g.max()

    volts = tem.groupby("voltage")["voltage"].mean()
    true_radius = HardCarbonPoreModel(pore_radius_angstrom=r).real_radius_angstrom
    
    ax.plot(
        avg, volts,
        marker="o",
        color=color,
        markerfacecolor="white",
        markeredgewidth=0.8,
        label=f'd = {2*true_radius/10:.1f} nm',
    )
    ax.fill_betweenx(
        volts, avg_min, avg_max,
        color=color,
        alpha=0.2
    )

# ax.axhline(0.1, label='0.1V')

ax.set_xlabel("Filling ratio (%)")
ax.set_ylabel("Voltage (V)")
ax.set_xlim(-0.5, 101)
ax.set_ylim(0, 1.5)
ax.legend()

fig.savefig(f"Figure4d.svg", bbox_inches="tight")
fig.savefig(f"Figure4d.png", bbox_inches="tight")
plt.show()

