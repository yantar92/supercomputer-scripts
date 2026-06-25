import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from pathlib import Path
from itertools import chain

sys.path.insert(0, "../mc-pore")
from mcpore import HardCarbonPoreModel

# DEFECTS="0.25"
RADII = [12, 20]

# defect_probabilities = [0.25, 0.17, 0.05, 0.01, 0]
defect_probabilities = [0, 0.05, 0.17, 0.25]


# --- Publication style (good for ~half A4 width figure) ---
a4_width = 4.13 * 2
width = a4_width * 1.06
height = width * 2 / 4 * 0.8
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


dfs = {}
names = ["Time", "Filling", "Formation energy"]
for radius in RADII:
    for defect in defect_probabilities:
        print(radius, defect)
        df = None
        max_idx = 100
        idx = 0
        if np.isclose(defect, 0):
            files = Path().glob(f"../14.fill_time_vs_radii/fix_samples_0V/0.00V_2000K_{radius}A_r*.csv.gz")
        else:
            files = Path().glob(f"fix_replicates/{defect:.2f}_{radius}A_r*.csv.gz")
        for f in files:
            idx += 1
            if idx > max_idx:
                continue
            print(f)
            df0 = pd.read_csv(f, names=names, skiprows=1)
            df0 = df0[::10]
            if df is None:
                df = df0
            else:
                df = pd.concat([df, df0])
        df = df.sort_values(by=["Time"])
        df = df.reset_index(drop=True)
        dfs[radius, defect] = df


# fig, (ax1, ax2) = plt.subplots(1, 2, width_ratios=[1, 1], sharey=True)
fig, ax = plt.subplots()
fig.subplots_adjust(wspace=0.05)  # adjust space between Axes

cmap = mpl.colormaps["tab10"]

# --- Build color map: defect -> fixed color ---
defect_colors = {}
for idx, defect in enumerate(defect_probabilities):
    defect_colors[defect] = cmap(idx)

# --- Plot: defect = color, radius = text label (all solid lines) ---
for rad_idx, radius in enumerate(RADII):
    for defect in defect_probabilities:
        df = dfs[radius, defect]
        df_median = df.groupby("Time").quantile(0.5)
        df_low = df.groupby("Time").quantile(0.25)
        df_high = df.groupby("Time").quantile(0.75)
        color = defect_colors[defect]
        ax.fill_between(df_median.index/100, df_low["Filling"], df_high["Filling"],
                        alpha=0.2, linewidth=0, color=color)
        ax.plot(df_median.index/100, df_median["Filling"],
                linewidth=1, color=color, linestyle="-")

# --- Defect legend (color only) ---
from matplotlib.lines import Line2D
defect_handles = [
    Line2D([0], [0], color=defect_colors[d], lw=1.5,
           label=f"{d*100:.0f}% defects")
    for d in defect_probabilities
]

ax.legend(handles=defect_handles, loc="lower right",
          title=None, ncols=2)

# --- Pore diameter labels placed near curves ---
for rad_idx, radius in enumerate(RADII):
    # Use the lowest-defect (0%) median curve for label placement
    df_median = dfs[radius, defect_probabilities[0]].groupby("Time").quantile(0.5)
    t_end = df_median[df_median["Filling"] > 99.99].index[0] / 100
    df_q1 = dfs[radius, defect_probabilities[0]].groupby("Time").quantile(0.25)
    f_end = df_q1["Filling"].iloc[-1]
    real_radius = HardCarbonPoreModel(pore_radius_angstrom=radius).real_radius_angstrom
    print(real_radius, t_end, f_end)
    ax.annotate(f"d = {2*real_radius/10:.2f} nm",
                xy=(t_end, f_end),
                xytext=(4, -4), textcoords="offset points",
                fontsize=11, ha="left", va="center")

ax.set_xlim(0, 15)
ax.set_ylim(20, 100)

ax.set_ylabel("Filling ratio (%)")
ax.set_xlabel("Time (a.u.)")

radii_str = "_".join(str(r) for r in RADII)
fig.savefig(f"fill_time_vs_defects_{radii_str}A.svg", bbox_inches="tight")
fig.savefig(f"fill_time_vs_defects_{radii_str}A.png", bbox_inches="tight")
# plt.show()
