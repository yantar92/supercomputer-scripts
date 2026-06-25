import pandas as pd
import matplotlib.pyplot as plt
from IMDgroup.utils.mpl import mpl_defaults, A4_WIDTH
from sklearn.metrics import mean_absolute_error, mean_squared_error

ALPHA = 1
MARKERSIZE = 3
MARKEREDGECOLOR = 'none'

df_d3 = pd.read_csv('formation_en_D3.txt', sep=' ')
df_opt = pd.read_csv('formation_en_opt.txt', sep=' ')
df_pbe = pd.read_csv('formation_en_MATPES.txt', sep=' ')
df_d3 = df_d3.sort_values(by='ID')
df_opt = df_opt.sort_values(by='ID')
df_pbe = df_pbe.sort_values(by='ID')

min_en_id = df_pbe[df_pbe['Energy'] == df_pbe['Energy'].min()]['ID'].iloc[0]
print(min_en_id)

mpl_defaults(width=A4_WIDTH)
fig, (ax1, ax2) = plt.subplots(1, 2)
df_pbe_common = df_pbe[df_pbe['ID'].isin(df_opt['ID'])]
df_opt_common = df_opt[df_opt['ID'].isin(df_pbe['ID'])]
en_ref_pbe = df_pbe[df_pbe['ID'] == min_en_id]['Energy'].iloc[0]
en_ref_opt = df_opt[df_opt['ID'] == min_en_id]['Energy'].iloc[0]
ax1.plot(
    df_pbe_common['Energy'] - en_ref_pbe,
    df_opt_common['Energy'] - en_ref_opt,
    'o', markersize=MARKERSIZE, alpha=ALPHA,
    markeredgecolor=MARKEREDGECOLOR)

mae = mean_absolute_error(df_pbe_common["Energy"] - en_ref_pbe,
                          df_opt_common["Energy"] - en_ref_opt)
ax1.text(.01, .99, f"MAE: {mae:.3} eV",
         ha='left', va='top',
         transform=ax1.transAxes)

ax1.axline((0, 0), slope=1, color='black')
ax1.set_xlim((0, 1))
ax1.set_ylim((0, 1))
ax1.set_title('Total energy: optB88-vdW vs PBE')
ax1.set_xlabel(f'PBE - reference ({min_en_id}), eV/atom')
ax1.set_ylabel(f'optB88-vdW - reference ({min_en_id}), eV/atom')

df_opt_common2 = df_opt[df_opt['ID'].isin(df_d3['ID'])]
df_d3_common2 = df_d3[df_d3['ID'].isin(df_opt['ID'])]
min_en_id = df_d3_common2[df_d3_common2['Energy'] == df_d3_common2['Energy'].min()]['ID'].iloc[0] 
en_ref_opt = df_opt[df_opt['ID'] == min_en_id]['Energy'].iloc[0]
en_ref_d3 = df_d3[df_d3['ID'] == min_en_id]['Energy'].iloc[0]
ax2.plot(
    df_d3_common2['Energy'] - en_ref_d3,
    df_opt_common2['Energy'] - en_ref_opt,
    'o', markersize=MARKERSIZE, alpha=ALPHA,
    markeredgecolor=MARKEREDGECOLOR)

mae = mean_absolute_error(df_d3_common2["Energy"] - en_ref_d3,
                          df_opt_common2["Energy"] - en_ref_opt)
ax2.text(.01, .99, f"MAE: {mae:.3} eV",
         ha='left', va='top',
         transform=ax2.transAxes)


ax2.axline((0, 0), slope=1, color='black')
ax2.set_xlim((0, 1))
ax2.set_ylim((0, 1))
ax2.set_title('Total energy: optB88-vdW vs PBE+D3-BJ')
ax2.set_xlabel(f'PBE+D3-BJ - reference ({min_en_id}), eV/atom')
ax2.set_ylabel(f'optB88-vdW - reference ({min_en_id}), eV/atom')

fig.savefig('energy-correlation.png', dpi=300)

