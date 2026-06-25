import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from IMDgroup.utils.mpl import mpl_defaults, A4_WIDTH
from sklearn.metrics import mean_absolute_error, mean_squared_error

ALPHA = 1
MARKERSIZE = 3
MARKEREDGECOLOR = 'none'
ENERGY_COL = 'Formation Energy (meV/atom)'
MAX_EN = 50
MIN_EN = -50
COLORMAP = 'viridis'

df_d3 = pd.read_csv('formation_en_D3.txt', sep=' ')
df_opt = pd.read_csv('formation_en_opt.txt', sep=' ')
df_pbe = pd.read_csv('formation_en_MATPES.txt', sep=' ')
df_d3 = df_d3.sort_values(by='ID')
df_opt = df_opt.sort_values(by='ID')
df_pbe = df_pbe.sort_values(by='ID')

# C = 0.03076923076923077
# df_d3 = df_d3[np.isclose(C, df_d3['Concentration'])]
# df_opt = df_opt[np.isclose(C, df_opt['Concentration'])]
# df_pbe = df_pbe[np.isclose(C, df_pbe['Concentration'])]

mpl_defaults(width=A4_WIDTH)
fig, (ax1, ax2) = plt.subplots(1, 2)
df_pbe_common = df_pbe[df_pbe['ID'].isin(df_opt['ID'])]
df_opt_common = df_opt[df_opt['ID'].isin(df_pbe['ID'])]
en_ref_pbe = 0
en_ref_opt = 0
ax1.scatter(
    df_pbe_common[ENERGY_COL] - en_ref_pbe,
    df_opt_common[ENERGY_COL] - en_ref_opt,
    c=df_pbe_common['Concentration'],
    norm=colors.Normalize(0, 0.1),
    cmap=COLORMAP,
    marker='o', s=MARKERSIZE, alpha=ALPHA,
    edgecolor=MARKEREDGECOLOR)

mae = mean_absolute_error(df_pbe_common[ENERGY_COL] - en_ref_pbe,
                          df_opt_common[ENERGY_COL] - en_ref_opt)
ax1.text(.01, .99, f"MAE: {mae:.3} meV",
         ha='left', va='top',
         transform=ax1.transAxes)

ax1.axline((0, 0), slope=1, color='black')
ax1.set_xlim((MIN_EN, MAX_EN))
ax1.set_ylim((MIN_EN, MAX_EN))
ax1.set_title('Formation energy: optB88-vdW vs PBE')
ax1.set_xlabel('PBE, meV/atom')
ax1.set_ylabel('optB88-vdW, meV/atom')

df_opt_common2 = df_opt[df_opt['ID'].isin(df_d3['ID'])]
df_d3_common2 = df_d3[df_d3['ID'].isin(df_opt['ID'])]
en_ref_opt = 0
en_ref_d3 = 0
sc =ax2.scatter(
    df_d3_common2[ENERGY_COL] - en_ref_d3,
    df_opt_common2[ENERGY_COL] - en_ref_opt,
    c=df_opt_common2['Concentration'],
    norm=colors.Normalize(0, 0.1),
    cmap=COLORMAP,
    marker='o', s=MARKERSIZE, alpha=ALPHA,
    edgecolor=MARKEREDGECOLOR)

plt.colorbar(sc, ax=ax2, label='Na concentration')

mae = mean_absolute_error(df_d3_common2[ENERGY_COL] - en_ref_d3,
                          df_opt_common2[ENERGY_COL] - en_ref_opt)
ax2.text(.01, .99, f"MAE: {mae:.3} meV",
         ha='left', va='top',
         transform=ax2.transAxes)


ax2.axline((0, 0), slope=1, color='black')
ax2.set_xlim((MIN_EN, MAX_EN))
ax2.set_ylim((MIN_EN, MAX_EN))
ax2.set_title('Formation energy: optB88-vdW vs PBE+D3-BJ')
ax2.set_xlabel('PBE+D3-BJ, meV/atom')
ax2.set_ylabel('optB88-vdW, meV/atom')

fig.savefig('energy-formation-correlation.png', dpi=300)

