#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:3]]
import matplotlib.pyplot as plt
from pymatgen.io.vasp import Vasprun
from pymatgen.electronic_structure.core import Spin
import argparse
import re
import os
import numpy as np


def main():
    """Main method
    """

    parser = argparse.ArgumentParser(
        description="""Plot DOS summary for different ISMEAR+SIGMA values""",
        epilog="""Author: Ihor Radchenko""",
    )

    args = parser.parse_args()

    vasp_dirs = []
    for root, dirs, files in os.walk('.'):
        if re.match(r'.*ISMEAR.*', root):
            vasp_dirs.append(root)
    vasp_dirs = sorted(vasp_dirs)

    energies = {'-5': [], '0': [], '1': []}
    for root in vasp_dirs:
        vasprun = Vasprun(os.path.join(root, 'vasprun.xml'))
        ismear = vasprun.incar['ISMEAR']
        sigma = vasprun.incar['SIGMA'] if 'SIGMA' in vasprun.incar else None
        efree = vasprun.as_dict()['output']['ionic_steps'][-1]['e_fr_energy']
        e_no_entropy = vasprun.as_dict()['output']['ionic_steps'][-1]['e_wo_entrp']
        e_0 = vasprun.as_dict()['output']['ionic_steps'][-1]['e_0_energy']

        energies[str(ismear)].append((sigma, efree, e_no_entropy, e_0))

    for ismear in energies.keys():
        if ismear == '-5':
            lnst = 'solid'
            plt.axhline(y=energies[ismear][0][1], label="Free", linestyle=lnst)
        else:
            if ismear == '0':
                lnst = 'dashed'
            else:
                lnst = 'dotted'
            
            plt.plot(
                [p[0] for p in energies[ismear]],
                [p[1] for p in energies[ismear]],
                label="Free",
                linestyle=lnst
            )

    for ismear in energies.keys():
        if ismear == '-5':
            lnst = 'solid'
            plt.axhline(y=energies[ismear][0][2], label="No entropy", linestyle=lnst)
        else:
            if ismear == '0':
                lnst = 'dashed'
            else:
                lnst = 'dotted'
            plt.plot(
                [p[0] for p in energies[ismear]],
                [p[2] for p in energies[ismear]],
                label=f"No entropy",
                linestyle=lnst
            )

    for ismear in energies.keys():
        if ismear == '-5':
            lnst = 'solid'
            plt.axhline(y=energies[ismear][0][3], label="sigma→0; ISMEAR=-5", linestyle=lnst)
        else:
            if ismear == '0':
                lnst = 'dashed'
            else:
                lnst = 'dotted'
            plt.plot(
                [p[0] for p in energies[ismear]],
                [p[3] for p in energies[ismear]],
                label=f"sigma→0; ISMEAR={ismear}",
                linestyle=lnst
            )

    plt.title(f"{os.path.basename(os.getcwd())}: Energy convergence for ISMEAR/SIGMA")
    plt.xlabel("Sigma (a.u.)")
    plt.ylabel("Energy (eV)")
    plt.legend(loc="upper left", ncol=3)
    # 0.001eV, as suggested in https://www.vasp.at/wiki/index.php/ISMEAR
    delta = 0.001
    e_opt = energies['-5'][0][1]
    plt.ylim(e_opt-delta, e_opt+delta)
    plt.xlim(0, 0.2)
    plt.savefig('energy.png')
    # plt.show()


if __name__ == "__main__":
    main()
# Scripts:3 ends here
