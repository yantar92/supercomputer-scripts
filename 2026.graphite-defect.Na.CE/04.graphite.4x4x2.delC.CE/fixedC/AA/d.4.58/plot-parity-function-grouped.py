import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as colors
import numpy as np
from IMDgroup.utils.mpl import mpl_defaults, A4_WIDTH
from sklearn.metrics import mean_absolute_error, mean_squared_error

ALPHA = 1
MARKERSIZE = 6
MARKEREDGECOLOR = 'none'
COLORBAR_ADDED = False

df_d3 = pd.read_csv('formation_en_D3.txt', sep=' ')
df_opt = pd.read_csv('formation_en_opt.txt', sep=' ')
df_pbe = pd.read_csv('formation_en_MATPES.txt', sep=' ')
df_d3 = df_d3.sort_values(by='ID')
df_opt = df_opt.sort_values(by='ID')
df_pbe = df_pbe.sort_values(by='ID')

def plot_conc(ax, df1, df2, concentration, add_colorbar=False):
    """Plot parity function for df1 vs df2 energies at given concentration.
    Return mean average error.
    """
    df1 = df1[df1['Concentration'] == concentration]
    df2 = df2[df2['Concentration'] == concentration]
    min_en_id = df1[df1['Energy'] == df1['Energy'].min()]['ID'].iloc[0]
    en_ref1 = df1[df1['ID'] == min_en_id]['Energy'].iloc[0]
    en_ref2 = df2[df2['ID'] == min_en_id]['Energy'].iloc[0]
    sc = ax.scatter(
        1000*(df1['Energy'] - en_ref1),
        1000*(df2['Energy'] - en_ref2),
        marker='o',
        c=[concentration / 0.3] * len(df1),
        norm=colors.Normalize(0, 0.3),
        s=MARKERSIZE, alpha=ALPHA,
        edgecolor=MARKEREDGECOLOR)
    global COLORBAR_ADDED
    if not COLORBAR_ADDED and add_colorbar:
        plt.colorbar(sc, ax=ax, label='Na concentration')
        COLORBAR_ADDED = True
    mae = mean_absolute_error(
        df1["Energy"] - en_ref1,
        df2["Energy"] - en_ref2)
    return mae*1000


mpl_defaults(width=A4_WIDTH)
fig, (ax1, ax2) = plt.subplots(1, 2)
df_pbe_common = df_pbe[df_pbe['ID'].isin(df_opt['ID'])]
df_opt_common = df_opt[df_opt['ID'].isin(df_pbe['ID'])]

maes = []
low_en_count = 0
for concentration in df_pbe_common['Concentration'].unique():
    maes.append(plot_conc(ax1, df_pbe_common, df_opt_common, concentration))
    df1 = df_pbe_common[df_pbe_common['Concentration'] == concentration]
    df2 = df_opt_common[df_opt_common['Concentration'] == concentration]
    min_en_id = df1[df1['Energy'] == df1['Energy'].min()]['ID'].iloc[0]
    en_ref1 = df1[df1['ID'] == min_en_id]['Energy'].iloc[0]
    low_en_count += len(df1[(df1['Energy'] - en_ref1) < 5/1000])
print(f"<10meV/atom: {low_en_count}/{len(df_pbe_common)} = {low_en_count/len(df_pbe_common)}")

mae = np.array(maes).mean()

ax1.text(.01, .99, f"MAE: {mae:.3} meV",
         ha='left', va='top',
         transform=ax1.transAxes)

ax1.axline((0, 0), slope=1, color='black')
ax1.set_title('optB88-vdW vs PBE')
ax1.set_xlabel('PBE, meV/atom')
ax1.set_ylabel('optB88-vdW, meV/atom')

df_opt_common2 = df_opt[df_opt['ID'].isin(df_d3['ID'])]
df_d3_common2 = df_d3[df_d3['ID'].isin(df_opt['ID'])]

maes = []
for concentration in df_opt_common2['Concentration'].unique():
    maes.append(plot_conc(ax2, df_d3_common2, df_opt_common2, concentration, True))

mae = np.array(maes).mean()

ax2.text(.01, .99, f"MAE: {mae:.3} meV",
         ha='left', va='top',
         transform=ax2.transAxes)

ax2.axline((0, 0), slope=1, color='black')
ax2.set_title('optB88-vdW vs PBE+D3-BJ')
ax2.set_xlabel('PBE+D3-BJ, meV/atom')
ax2.set_ylabel('optB88-vdW, meV/atom')

plt.suptitle('Energy above opt GS structure')

fig.savefig('energy-above-hull-correlation.png', dpi=300)

