#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*DOS plot - Sasha's version][DOS plot - Sasha's version:1]]
import matplotlib.pyplot as plt
from pymatgen.io.vasp import Vasprun
from pymatgen.electronic_structure.core import Spin
import argparse
import numpy as np

parser = argparse.ArgumentParser(
    description="""Plot DOS""",
    epilog="""Author: Ihor Radchenko""",
)

parser.add_argument(
    "--enrange",
    help="Energy range to be plotted as enmin:enmacs",
    default=None,
    type=str)

parser.add_argument(
    "--dosrange",
    help="DOS range to be plotted as dosmin:dosmax",
    default=None,
    type=str)

parser.add_argument(
    "--diff",
    help="When provided, plot difference between spin up/down curves",
    action='store_true')


args = parser.parse_args()


vasprun = Vasprun("vasprun.xml", parse_dos=True)
total_dos = vasprun.complete_dos
energies = np.array(total_dos.energies) - vasprun.efermi
system_name = vasprun.incar['SYSTEM']
if system_name is None:
    system_name = "Unknown system"

if Spin.down in total_dos.densities:
    dos_up = total_dos.densities[Spin.up]
    dos_down = total_dos.densities[Spin.down]
    plt.plot(energies, dos_up, label="Spin Up")
    down_plot = plt.plot(energies, -dos_down, label="Spin Down")  
    # Plot the difference
    if args.diff:
        plt.fill_between(
            energies, dos_up, dos_down,
            color=down_plot[0].get_color(),
            alpha=0.1,
            label="Spin Up - Down")
else:
    dos_up = total_dos.densities[Spin.up]
    plt.plot(energies, dos_up, label="Total DOS")


# Indicate Fermi energy; we shifted DOS by Fermi energy, so it must be at 0 now
plt.axvline(x=0, color='r', label='Fermi energy')

plt.title(f"{system_name}: Total DOS (Total energy = {vasprun.final_energy})")
plt.xlabel("Energy (eV)")
plt.ylabel("DOS (1/eV/cell)")
if args.enrange is not None:
    enmin, enmacs = tuple(map(float, args.enrange.split(':')))
    plt.xlim(enmin, enmacs)
if args.dosrange is not None:
    dosmin, dosmax = tuple(map(float, args.dosrange.split(':')))
    plt.ylim(dosmin, dosmax)
plt.legend()
plt.savefig('dos.png')
# plt.show()
# DOS plot - Sasha's version:1 ends here
