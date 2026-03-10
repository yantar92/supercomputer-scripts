import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

base_path_Na = Path("~/helios/0000.lumi/2025.graphite-exanded.Na.CE/04.CE.relax.KPOINTS.10k")
base_path_Li = Path("~/helios/0000.lumi/2025.graphite.Li.CE/04.CE.relax.KPOINTS.10k")

def read_voltage(p: Path) -> pd.DataFrame:
    return pd.read_csv(
        p / 'voltage.out', sep=' ')

dfs_Na = []

dfs_Na.append(read_voltage(base_path_Na / "AA" / "strain.c.0.00"))
dfs_Na[-1].d_spacing = 3.52
dfs_Na[-1].linewidth = 1
dfs_Na[-1].ion = "Na"
dfs_Na[-1].stacking = "AA"
dfs_Na.append(read_voltage(base_path_Na / "AA" / "strain.c.0.13"))
dfs_Na[-1].d_spacing = 3.99
dfs_Na[-1].linewidth = 2
dfs_Na[-1].ion = "Na"
dfs_Na[-1].stacking = "AA"
dfs_Na.append(read_voltage(base_path_Na / "AA" / "strain.c.0.30.c1.0.33.check_relax"))
dfs_Na[-1].d_spacing = 4.58
dfs_Na[-1].linewidth = 3
dfs_Na[-1].ion = "Na"
dfs_Na[-1].stacking = "AA"
# dfs_Na.append(read_voltage(base_path_Na / "AB" / "strain.equal.AA.c.0.00.sparse.sublattice-2"))
# dfs_Na[-1].d_spacing = 3.52
# dfs_Na[-1].linewidth = 1
# dfs_Na[-1].ion = "Na"
# dfs_Na[-1].stacking = "AB"
# dfs_Na.append(read_voltage(base_path_Na / "AB" / "strain.equal.AA.c.0.15.sparse.sublattice"))
# dfs_Na[-1].d_spacing = 3.99
# dfs_Na[-1].linewidth = 2
# dfs_Na[-1].ion = "Na"
# dfs_Na[-1].stacking = "AB"
# dfs_Na.append(read_voltage(base_path_Na / "AB" / "strain.equal.AA.c.0.30.sparse.sublattice"))
# dfs_Na[-1].d_spacing = 4.58
# dfs_Na[-1].linewidth = 3
# dfs_Na[-1].ion = "Na"
# dfs_Na[-1].stacking = "AB"

dfs_Li = []

dfs_Li.append(read_voltage(base_path_Li / "AA" / "strain.c.0.00"))
dfs_Li[-1].d_spacing = 3.48
dfs_Li[-1].linewidth = 1
dfs_Li[-1].ion = "Li"
dfs_Li[-1].stacking = "AA"
dfs_Li.append(read_voltage(base_path_Li / "AA" / "strain.c.0.15"))
dfs_Li[-1].d_spacing = 4.00
dfs_Li[-1].linewidth = 2
dfs_Li[-1].ion = "Li"
dfs_Li[-1].stacking = "AA"
dfs_Li.append(read_voltage(base_path_Li / "AA" / "strain.c.0.30.simplify.sublattice"))
dfs_Li[-1].d_spacing = 4.53
dfs_Li[-1].linewidth = 3
dfs_Li[-1].ion = "Li"
dfs_Li[-1].stacking = "AA"
dfs_Li.append(read_voltage(base_path_Li / "AB" / "strain.equal.AA.c.0.00.sparse.sublattice"))
dfs_Li[-1].d_spacing = 3.48
dfs_Li[-1].linewidth = 1
dfs_Li[-1].ion = "Li"
dfs_Li[-1].stacking = "AB"
dfs_Li.append(read_voltage(base_path_Li / "AB" / "strain.equal.AA.c.0.15.sparse.sublattice"))
dfs_Li[-1].d_spacing = 4.00
dfs_Li[-1].linewidth = 2
dfs_Li[-1].ion = "Li"
dfs_Li[-1].stacking = "AB"
# dfs_Li.append(read_voltage(base_path_Li / "AB" / "strain.equal.AA.c.0.30.sparse.sublattice"))
# dfs_Li[-1].d_spacing = 4.58
# dfs_Li[-1].linewidth = 3
# dfs_Li[-1].ion = "Li"
# dfs_Li[-1].stacking = "AB"

# fig, axs = plt.subplots(1, 2, figsize=(20, 6))
plt.rcParams.update({'font.size': 16})
fig, ax = plt.subplots(1, 1, figsize=(9, 5.4))
axs = [ax]
for ax in axs:
    ax.axhline(y=0, color='gray', linestyle='-', alpha=0.7, linewidth=0.5)
    ax.set_xlim((0.1, 1.1))
axs[0].set_ylim((-1.7, 0.4))
# axs[1].set_ylim((-1, 1))
axs[0].set_xlabel(f'Concentration (x in Na$_{{x}}$C$_{6}$)')
axs[0].set_ylabel("Voltage vs Na/Na⁺ (V)")
# axs[0].set_title('Na intercalation', fontsize=16)
# axs[1].set_xlabel(f'Concentration (x in Li$_{{x}}$C$_{6}$)', fontsize=16)
# axs[1].set_ylabel("Voltage vs Li/Li^+ (V)", fontsize=16)
# axs[1].set_title('Li intercalation', fontsize=16)
for df in dfs_Na:
    axs[0].step(
        df['x']*6,
        df['voltage'],
        where='post',
        linewidth=2,
        label=" d$_{002}$: "+str(df.d_spacing)+"Å",
        linestyle='-' if df.stacking == "AA" else "--")
# for df in dfs_Li:
#     axs[1].step(
#         df['x']*6,
#         df['voltage'],
#         where='post',
#         label=df.stacking + " d$_{002}$: "+str(df.d_spacing)+"Å",
#         linestyle='-' if df.stacking == "AA" else "--")
for ax in axs:
    ax.legend()
plt.savefig("data.png", dpi=300)
