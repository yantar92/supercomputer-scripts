#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:2]]
import matplotlib.pyplot as plt
from pymatgen.io.vasp import Vasprun
from pymatgen.electronic_structure.core import Spin
import argparse
import re
import os
import numpy as np


def add_dos_plot(vasprun, yoffset=0, xoffset=0):
    """Plot DOS from VASPRUN to axis.
    X/YOFFSET is the offset to be used.
    """

    total_dos = vasprun.complete_dos
    energies = np.array(total_dos.energies) - vasprun.efermi + xoffset
    dos_up = np.array(total_dos.densities[Spin.up]) + yoffset

    ismear = vasprun.incar['ISMEAR']
    sigma = vasprun.incar['SIGMA'] if 'SIGMA' in vasprun.incar else None
    if sigma is None:
        label = f"ISMEAR:{ismear}"
    else:
        label = f"ISMEAR:{ismear} SIGMA:{sigma}"
    
    plt.plot(energies, dos_up, label=label)


def main():
    """Main method
    """

    parser = argparse.ArgumentParser(
        description="""Plot DOS summary for different ISMEAR+SIGMA values""",
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
        "--xoffset",
        help="X axis offset between different ISMEAR values",
        default=0,
        type=float)

    parser.add_argument(
        "--yoffset",
        help="Y axis offset between different SIGMA values",
        default=0,
        type=float)

    args = parser.parse_args()

    plt.figure(figsize=(20,10))

    vasp_dirs = []
    for root, dirs, files in os.walk('.'):
        if re.match(r'.*ISMEAR.*', root):
            vasp_dirs.append(root)
    vasp_dirs = sorted(vasp_dirs)

    current_offset_0 = 0
    current_offset_1 = 0
    current_offset_5 = 0
    yoffset_delta = args.yoffset
    xoffset_delta = args.xoffset

    for root in vasp_dirs:
        vasprun = Vasprun(os.path.join(root, 'vasprun.xml'), parse_dos=True)
        ismear = vasprun.incar['ISMEAR']
        if ismear == -5:
            current_offset_5 += yoffset_delta
            add_dos_plot(vasprun, yoffset=current_offset_5, xoffset = 0)
        elif ismear == 0:
            current_offset_0 += yoffset_delta
            add_dos_plot(vasprun, yoffset=current_offset_0, xoffset = 1*xoffset_delta)
        else:
            current_offset_1 += yoffset_delta
            add_dos_plot(vasprun, yoffset=current_offset_1, xoffset = 2*xoffset_delta)

    # Indicate Fermi energy; we shifted DOS by Fermi energy, so it must be at 0 now
    plt.axvline(x=0, color='r', label='Fermi energy')
    plt.axvline(x=1*xoffset_delta, color='r')
    plt.axvline(x=2*xoffset_delta, color='r')

    plt.title(f"{os.path.basename(os.getcwd())}: Total DOS")
    plt.xlabel("Energy (eV)")
    plt.ylabel("DOS (1/eV/cell)")
    if args.enrange is not None:
        enmin, enmacs = tuple(map(float, args.enrange.split(':')))
        plt.xlim(enmin, enmacs)
    if args.dosrange is not None:
        dosmin, dosmax = tuple(map(float, args.dosrange.split(':')))
        plt.ylim(dosmin, dosmax)
    plt.legend(bbox_to_anchor=(1.04, 1), loc="upper left", ncol=1)
    plt.subplots_adjust(right=0.85)
    plt.savefig('dos.png')
    # plt.show()


if __name__ == "__main__":
    main()
# Scripts:2 ends here
