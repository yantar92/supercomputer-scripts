from pathlib import Path
import numpy as np
import pandas as pd
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir
import matplotlib.pyplot as plt
from IMDgroup.utils.mpl import mpl_defaults, A4_WIDTH
from sklearn.metrics import mean_absolute_error, mean_squared_error

ALPHA = 0.5
MARKERSIZE = 3
MARKEREDGECOLOR = 'none'

vaspdirs_opt = IMDGVaspDir.read_vaspdirs(
    '.', path_filter=lambda d: d.name == 'relax.2.optB88-vdW')
print(f"optB88-vdW: {len(vaspdirs_opt)}")
print(vaspdirs_opt.keys()) 
vaspdirs_pbe = IMDGVaspDir.read_vaspdirs(
    '.', path_filter=lambda d:
    (d.parent.name == 'relax.final') and
    (((d.parent / 'gorun_8').is_dir() and d.name == 'gorun_5') or
     ((not (d.parent / 'gorun_8').is_dir()) and d.name == 'gorun_4')))
print(f"PBE: {len(vaspdirs_pbe)}")
print(vaspdirs_pbe.keys())
# vaspdirs_d3 = IMDGVaspDir.read_vaspdirs(
#     '.', path_filter=lambda d: d.name == 'ATAT.SCF.MATPES.PBE+D3-BJ')

ids_pbe = []
forces_pbe = []
ids_opt = []
forces_opt = []
ids_d3 = []
forces_d3 = []

for d in vaspdirs_opt:
    path_opt = Path(d)
    parent = path_opt.parent
    path_pbe = parent / 'relax.final'
    # path_d3 = parent / 'ATAT.SCF.MATPES.PBE+D3-BJ'
    idx = str(parent)

    vdir_opt = vaspdirs_opt.get(str(path_opt))
    # print(str(path_pbe / 'gorun_5'))
    vdir_pbe = vaspdirs_pbe.get(str(path_pbe / 'gorun_5'))
    if vdir_pbe is None:
        vdir_pbe = vaspdirs_pbe.get(str(path_pbe / 'gorun_4'))
        print(str(path_pbe), 'gorun_4')
    else:
        print(str(path_pbe), 'gorun_5')
    if vdir_opt is None or vdir_pbe is None:
        print('1 of 2 EMPTY')
        continue
    
    for ids, forces, vdir in [(ids_opt, forces_opt, vdir_opt),
                              (ids_pbe, forces_pbe, vdir_pbe),
                              # (ids_d3, forces_d3, vaspdirs_d3.get(str(path_d3))),
                              ]:
        if vdir is None:
            print('EMPTY')
            continue
        na_fraction = vdir.structure.composition.get_atomic_fraction('Na')
        # print(na_fraction)
        # Na7C60 - GS
        if not np.isclose(7 / 67, na_fraction):
            break
        print(d)
        if not (vdir.converged_ionic and vdir.converged_electronic):
            print('UNCONVERGED')
            break
        new_forces = vdir['vasprun.xml'].ionic_steps[-1]['forces']
        new_forces = list(np.array(new_forces).flatten())
        if forces is forces_opt:
            print('optB88-vdW')
        else:
            print('PBE')
        print(f"Max force: {np.max(new_forces)}")
        new_ids = [idx] * len(new_forces)
        print(f"added {len(new_forces)} forces")
        ids += new_ids
        forces += new_forces

df_opt = pd.DataFrame({'ID': ids_opt, 'force': forces_opt})
df_pbe = pd.DataFrame({'ID': ids_pbe, 'force': forces_pbe})
# df_d3 = pd.DataFrame({'ID': ids_d3, 'force': forces_d3})

print(df_opt['ID'].unique())
print(df_pbe['ID'].unique())

mpl_defaults(width=A4_WIDTH)



# optB88-vdW vs PBE
df_opt_common = df_opt[df_opt['ID'].isin(df_pbe['ID'])]
df_pbe_common = df_pbe[df_pbe['ID'].isin(df_opt['ID'])]

# fig, (ax1, ax2) = plt.subplots(1, 2)
fig, ax1 = plt.subplots()

ax1.plot(df_pbe_common['force'], df_opt_common['force'],
         'o', markersize=MARKERSIZE, alpha=ALPHA,
         markeredgecolor=MARKEREDGECOLOR)

mae = mean_absolute_error(df_pbe_common["force"], df_opt_common["force"])
ax1.text(.01, .99, f"MAE: {mae:.3} eV/A",
         ha='left', va='top',
         transform=ax1.transAxes)

ax1.axline((0, 0), slope=1, color='black')
ax1.set_title('All force components: optB88-vdW vs PBE')
ax1.set_xlabel('PBE, eV/A')
ax1.set_ylabel('optB88-vdW, eV/A')

# optB88-vdW vs PBE+D3-BJ
# df_opt_common = df_opt[df_opt['ID'].isin(df_d3['ID'])]
# df_d3_common = df_d3[df_d3['ID'].isin(df_opt['ID'])]

# ax2.plot(df_d3_common['force'], df_opt_common['force'],
#          'o', markersize=MARKERSIZE, alpha=ALPHA,
#          markeredgecolor=MARKEREDGECOLOR)

# mae = mean_absolute_error(df_d3_common["force"], df_opt_common["force"])
# ax2.text(.01, .99, f"MAE: {mae:.3} eV/A",
#          ha='left', va='top',
#          transform=ax2.transAxes)

# ax2.axline((0, 0), slope=1, color='black')
# ax2.set_title('All force components: optB88-vdW vs PBE+D3-BJ')
# ax2.set_xlabel('PBE+D3-BJ, eV/A')
# ax2.set_ylabel('optB88-vdW, eV/A')
fig.savefig('force-correlations.png', dpi=300)
