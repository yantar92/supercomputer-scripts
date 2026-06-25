from cycler import cycler
import pandas as pd
import matplotlib.pyplot as plt
from IMDgroup.utils.mpl import mpl_defaults, A4_WIDTH

voltage15 = pd.read_csv('PBE/CNT_15,0_1_10.0/voltage.out', sep=' ')
voltage17 = pd.read_csv('optB88-vdW/CNT_17,0_1_10.0/voltage.out', sep=' ')
voltage20 = pd.read_csv('PBE/CNT_20,0_1_10.0/voltage.out', sep=' ')

mpl_defaults(font_size=8, width=A4_WIDTH * 0.75, ratio=2.5)
colors = plt.cm.tab10(range(0, 10, 1))
dashes = ['-', '--', '-.', ':']
custom_cycler = (cycler(linestyle=dashes) * cycler(color=colors))
plt.rc('axes', prop_cycle=custom_cycler)
plt.tight_layout()
plt.axhline(0, color='black', linewidth=0.5)
n_c = 60
n_na = voltage15['x'] * n_c
plt.plot(n_na / (n_na + n_c), voltage15['voltage'], '-', label='CNT15,0: D = 1.2 nm', linewidth=2)
n_c = 68
n_na = voltage17['x'] * n_c
plt.plot(n_na / (n_na + n_c), voltage17['voltage'], '-', label='CNT17,0: D = 1.3 nm', linewidth=2)
n_c = 80
n_na = voltage20['x'] * n_c
plt.plot(n_na / (n_na + n_c), voltage20['voltage'], '-', label='CNT20,0: D = 1.6 nm', linewidth=2)
plt.ylim((-0.03, 0.3))
plt.xlim((0, 0.188))
plt.xlabel('Na concentration, a.u.')
plt.ylabel('Voltage vs. Na/Na$^{+}$, V')
plt.legend()

plt.savefig('voltages.png', dpi=300)
plt.savefig('voltages.svg', dpi=300)
plt.clf()
