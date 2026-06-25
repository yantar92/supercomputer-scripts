import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from pathlib import Path

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


names = ["Time", "Filling", "Formation energy"]

all_df = pd.read_csv(
    'fix_samples/results.csv',
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
all_df['mcs'] = all_df['mcs']/100
all_df['fill_mcs'] = all_df['fill_mcs']/100

# fig, (ax1, ax2) = plt.subplots(1, 2, width_ratios=[1, 1], sharey=True)
fig, ax = plt.subplots()
fig.subplots_adjust(wspace=0.05)  # adjust space between Axes

cmap = mpl.colormaps["tab20"]

TEMPERATURE = 2000
VOLTAGE = 0.00
DEFECT_CONCENTRATION = 0

radii = all_df['radius'].unique()
# sel = np.r_[radii[radii < 10.0], radii[radii >= 10.0][::2]]
# sel = [7,8,12,15,17,20]
radii = sorted(radii)

# all_df = all_df[np.isclose(all_df["final_filling"], 100)]
all_df['voltage'] = pd.to_numeric(all_df['voltage'])

print(all_df['temperature'].unique())

# all_df = all_df[np.isclose(all_df['temperature'], TEMPERATURE)]
all_df = all_df[np.isclose(all_df['defect_probability'], DEFECT_CONCENTRATION)]
all_df = all_df[np.isclose(all_df['voltage'], VOLTAGE)]

for idx, temp in enumerate(sorted(all_df['temperature'].unique())):
    # if np.isclose(temp, 1200):
    #     continue
    if np.isclose(temp, 4000):
        continue
    df = all_df[np.isclose(all_df['temperature'], temp)]
    data = {'radius': [], 'fill_time': [], 'fill_time_min': [], 'fill_time_max': []}
    for r in radii:
        tem = df[np.isclose(df["radius"], r)]
        data['radius'].append(r)
        data['fill_time'].append(tem['fill_mcs'].mean())
        data['fill_time_min'].append(tem['fill_mcs'].min())
        data['fill_time_max'].append(tem['fill_mcs'].max())

    ax.plot(
        2*np.array(data['radius'])/10, data['fill_time'],
        "o",
        markeredgewidth=0.8,
        label=f"{temp}K",
        color=cmap(idx)
    )
    ax.fill_between(
        2*np.array(data['radius'])/10, data['fill_time_min'], data['fill_time_max'],
        alpha=0.3, color=cmap(idx)
    )
    
ax.legend()



# ax.set_ylim(0, 20)
# ax.set_ylim(20, 100)

# ax.axhline(100, color='black', linewidth=0.8)
# ax1.plot(df['Time']/1000, df['Filling'], color='black',linewidth=0.8)
# ax2.plot(df['Time']/1000, df['Filling'], color='black', linewidth=0.8)

ax.set_ylabel("Filling time (a.u.)")
ax.set_xlabel("Pore diameter (nm)")

# ax.legend(ncols=2)

fig.savefig(f"fill-time.svg", bbox_inches="tight")
fig.savefig(f"fill-time.png", bbox_inches="tight")
plt.show()

