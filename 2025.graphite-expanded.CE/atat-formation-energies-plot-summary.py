import numpy as np
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

# --- fake data -----------------------------------------------------------
li = np.random.uniform(-40, 30, size=(5, 5))
na = np.random.uniform(-40, 30, size=(5, 5))

x_vals = [3.52, 3.75, 3.99, 4.25, 4.58]
stoich_labels = ["C16", "C20", "C24", "C28", "C56"]

vmin, vmax = -40, 30

# --- figure & gridspec: NO tight_layout / constrained_layout ------------
fig = plt.figure(figsize=(7, 4))

# 3 columns: Li, Na, colorbar; wspace=0 makes Li/Na touch
gs = GridSpec(
    1, 3,
    figure=fig,
    width_ratios=[1, 1, 0.05],
    wspace=0.0,
)

ax_li = fig.add_subplot(gs[0, 0])
ax_na = fig.add_subplot(gs[0, 1], sharey=ax_li)
cax   = fig.add_subplot(gs[0, 2])

# --- Li heatmap ---------------------------------------------------------
im_li = ax_li.imshow(li, origin="lower", vmin=vmin, vmax=vmax, aspect="auto")
ax_li.set_xticks(range(len(x_vals)))
ax_li.set_xticklabels(x_vals)
ax_li.set_yticks(range(len(stoich_labels)))
ax_li.set_yticklabels(stoich_labels)
ax_li.set_ylabel("Stoichiometry (Cₓ)")
ax_li.set_title("Li", pad=10)
# only left-side ticks
ax_li.tick_params(axis="y", right=False)

# remove right spine so panels visually merge
ax_li.spines["right"].set_visible(False)

# --- Na heatmap ---------------------------------------------------------
im_na = ax_na.imshow(na, origin="lower", vmin=vmin, vmax=vmax, aspect="auto")
ax_na.set_xticks(range(len(x_vals)))
ax_na.set_xticklabels(x_vals)
ax_na.set_yticklabels([])   # share y from left
ax_na.set_title("Na", pad=10)
ax_na.tick_params(axis="y", left=False)   # remove middle ticks

# remove left spine of Na panel
ax_na.spines["left"].set_visible(False)

# optional: vertical separator line at the interface
ax_na.axvline(-0.5, color="k", linewidth=2)

# --- colorbar -----------------------------------------------------------
cbar = fig.colorbar(im_li, cax=cax)
cbar.set_label("Formation energy (meV/atom)")

# shared x-label
fig.text(
    0.5, 0.04,
    "Interlayer distance (Å): Li (columns 0–4) | Na (columns 5–9)",
    ha="center", va="center"
)

plt.show()
