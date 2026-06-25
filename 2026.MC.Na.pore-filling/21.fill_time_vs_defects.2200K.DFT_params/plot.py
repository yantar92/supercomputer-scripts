import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from pathlib import Path
from itertools import chain

# DEFECTS="0.25"
RADIUS = "20"

# read DEFECTS from command arguments
if len(sys.argv) > 1:
    RADIUS = sys.argv[1]

# radii = np.arange(5, 31, 1, dtype='int')
# radii = [7,8,12,15,17,20]
# radii = [7,8,12,15,17,20]
# defect_probabilities = [0.25, 0.17, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01]
defect_probabilities = [0.25, 0.17, 0.05, 0.01, 0]


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


dfs = {}
names = ["Time", "Filling", "Formation energy"]
for defect in defect_probabilities:
    print(defect)
    df = None
    max_idx = 100
    idx = 0
    if np.isclose(defect, 0):
        files = Path().glob(f"../20.fill_time_vs_radii_DFT_params/fix_samples_0V/0.00V_2000K_{RADIUS}A_r*.csv.gz")
    else:
        files = Path().glob(f"fix_replicates/{defect:.2f}_{RADIUS}A_r*.csv.gz")
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
    dfs[defect] = df


# fig, (ax1, ax2) = plt.subplots(1, 2, width_ratios=[1, 1], sharey=True)
fig, ax = plt.subplots()
fig.subplots_adjust(wspace=0.05)  # adjust space between Axes

cmap = mpl.colormaps["tab10"]

# df2=df[::100]

for idx, defect in enumerate(reversed(defect_probabilities)):
    df = dfs[defect]
    df_mean = df.groupby("Time").mean()
    df_median = df.groupby("Time").quantile(0.5)
    df_low = df.groupby("Time").quantile(0.25)
    df_high = df.groupby("Time").quantile(0.75)
    df_min = df.groupby("Time").min()
    df_max = df.groupby("Time").max()
    print(len(df_mean), len(df_median), len(df_high), len(df_low))
    ax.fill_between(df_mean.index/100, df_low["Filling"], df_high["Filling"], alpha=0.2, linewidth=0, color=cmap(idx))
    ax.plot(df_median.index/100, df_median["Filling"], label=f"{defect*100:.2f}%", linewidth=1, color=cmap(idx))
    # ax.plot(df["Time"]/100, df["Filling"], linewidth=0.1, alpha=0.1, color=cmap(idx))
    # ax.plot(df_mean.index/100, df_mean["Filling"], label=f"$d$ = {radius*2/10} nm", linewidth=1, color=cmap(idx))

# ax.set_xlim(0, 250)
ax.set_xlim(0, 15)
ax.set_ylim(20, 100)

# ax.axhline(100, color='black', linewidth=0.8)
# ax1.plot(df['Time']/1000, df['Filling'], color='black',linewidth=0.8)
# ax2.plot(df['Time']/1000, df['Filling'], color='black', linewidth=0.8)

ax.set_ylabel("Filling ratio (%)")
ax.set_xlabel("Time (a.u.)")

# ax.set_ylabel("Filling ratio (%)")
# ax.set_xlabel("Time (a.u.)")


# ax1.xaxis.set_ticks(np.arange(0, 500, 100))
# ax1.yaxis.set_ticks(np.arange(0, 100, 10))
# ax2.xaxis.set_ticks(np.arange(1000, 22000, 5000))

# split axes
# d = 1.0  # proportion of vertical to horizontal extent of the slanted line
# kwargs = dict(marker=[(-1, -d), (1, d)], markersize=5,
#               linestyle="none", color='k', mec='k', mew=1, clip_on=False)
# ax1.plot([1, 1], [1, 0], transform=ax1.transAxes, **kwargs)
# ax2.plot([0, 0], [0, 1], transform=ax2.transAxes, **kwargs)

# hide the spines between ax and ax2
# ax1.spines.right.set_visible(False)
# ax2.spines.left.set_visible(False)
# ax1.yaxis.tick_left()
# ax1.tick_params(labeltop=False)  # don't put tick labels at the top
# ax2.yaxis.tick_right()

ax.legend(ncols=2)
# ax.legend(ncols=4)

# sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
# sm.set_array([])
# cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06)
# cbar.set_label("Pore radius (Å)")
# cbar.ax.tick_params(direction="out")

# fig.savefig(f"{DEFECTS}.svg", bbox_inches="tight")
# fig.savefig(f"{DEFECTS}.png", bbox_inches="tight")
fig.savefig(f"fill_time_vs_defects_{RADIUS}A.svg", bbox_inches="tight")
fig.savefig(f"fill_time_vs_defects_{RADIUS}A.png", bbox_inches="tight")
plt.show()

