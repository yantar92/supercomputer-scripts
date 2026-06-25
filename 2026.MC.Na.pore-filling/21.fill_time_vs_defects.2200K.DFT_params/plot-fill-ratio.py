import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import matplotlib as mpl
from pathlib import Path
import itertools

sys.path.insert(0, "../mc-pore")
from mcpore import HardCarbonPoreModel

# constant time
TIME = 500

if len(sys.argv) > 1:
    TIME = float(sys.argv[1])

radii = np.arange(5, 31, 1, dtype='int')
# radii = [7,8,12,15,17,20]
# radii = [7,8,15,20]
# defect_probabilities = [0.25, 0.17, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01]
# defect_probabilities = [0.25, 0.17, 0.05, 0.01, 0]
defect_probabilities = [0, 0.17, 0.25]


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

df_all = None
names = ["Time", "Filling", "Formation energy"]
for r in radii:
    for defect in defect_probabilities:
        print(defect)
        max_idx = 100
        idx = 0
        if np.isclose(defect, 0):
            files = Path().glob(f"../20.fill_time_vs_radii_DFT_params/fix_samples_0V/0.00V_2200K_{r}A_r*.csv.gz")
        else:
            files = Path().glob(f"fix_replicates/{defect:.2f}_{r}A_r*.csv.gz")
        for f in files:
            idx += 1
            if idx > max_idx:
                continue
            print(f)
            df0 = pd.read_csv(f, names=names, skiprows=1)
            df0 = df0[np.isclose(df0['Time'], TIME, atol=1)]
            print(df0)
            # df0 = df0[::10]
            # df0 = df0.sort_values(by=["Time"])
            # df0 = df0.reset_index(drop=True)
            df0['Time'] = df0['Time']/100
            df0['Defect'] = defect
            df0['Radius'] = HardCarbonPoreModel(pore_radius_angstrom=r).real_radius_angstrom
            if df_all is None:
                df_all = df0
            else:
                df_all = pd.concat([df_all, df0])

# fig, (ax1, ax2) = plt.subplots(1, 2, width_ratios=[1, 1], sharey=True)
fig, ax = plt.subplots()
fig.subplots_adjust(wspace=0.05)  # adjust space between Axes

cmap = mpl.colormaps["tab10"]

# df2=df[::100]

data = {'radius': [], 'fill_median': [], 'fill_q1': [], 'fill_q3': []}

for idx, defect in enumerate(defect_probabilities):
    df = df_all[np.isclose(df_all['Defect'], defect)]
    print(df)
    df_median = df.groupby("Radius").quantile(0.5)
    df_low = df.groupby("Radius").quantile(0.25)
    df_high = df.groupby("Radius").quantile(0.75)
    ax.fill_between(df_median.index*2/10, df_low["Filling"], df_high["Filling"], alpha=0.2, linewidth=0, color=cmap(idx))
    ax.plot(
        df_median.index*2/10, df_median["Filling"],
        "o",
        markerfacecolor=cmap(idx),
        markeredgewidth=0.8,
        label=f"{defect*100:.2f}% defects", color=cmap(idx))
    # ax.errorbar(
    #     df_median.index*2/10, df_median["Filling"],
    #     yerr=[df_median['Filling'] - df_low['Filling'],
    #           df_high['Filling'] - df_median['Filling']],
    #     fmt="o",
    #     markerfacecolor=cmap(idx),
    #     markeredgewidth=0.8,
    #     elinewidth=0.5,
    #     label=f"{defect*100:.2f}% defects", color=cmap(idx))

    from scipy.interpolate import UnivariateSpline
    s = UnivariateSpline(df_median.index*2/10, df_median["Filling"], s=len(df_median.index)*50)
    xnew = np.linspace(df_median.index[0]*2/10, df_median.index[-1]*2/10, num=100, endpoint=True)
    ax.plot(xnew, s(xnew), color=cmap(idx), linewidth=1)
    
    

# ax.set_xlim(0, 250)
# ax.set_xlim(0, 15)
ax.set_ylim(0, 105)

# ax.axhline(100, color='black', linewidth=0.8)
# ax1.plot(df['Time']/1000, df['Filling'], color='black',linewidth=0.8)
# ax2.plot(df['Time']/1000, df['Filling'], color='black', linewidth=0.8)

ax.set_ylabel("Filling ratio (%)")
ax.set_xlabel("Diameter, nm")

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

ax.legend(ncols=1)
# ax.legend(ncols=4)

# sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
# sm.set_array([])
# cbar = fig.colorbar(sm, ax=ax, pad=0.02, fraction=0.06)
# cbar.set_label("Pore radius (Å)")
# cbar.ax.tick_params(direction="out")

# fig.savefig(f"{DEFECTS}.svg", bbox_inches="tight")
# fig.savefig(f"{DEFECTS}.png", bbox_inches="tight")
fig.savefig(f"fill_ratio_vs_radius_at_{TIME}.svg", bbox_inches="tight")
fig.savefig(f"fill_ratio_vs_radius_at_{TIME}.png", bbox_inches="tight")
plt.show()

