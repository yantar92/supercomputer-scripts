#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:3]]
"""Analyze interatomic distances from the Vasprun."""

import argparse
import os
import re
from tabulate import tabulate
import multiprocessing
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.apps.borg.hive import SimpleVaspToComputedEntryDrone, VaspToComputedEntryDrone
from pymatgen.apps.borg.queen import BorgQueen

def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""Analyze changes in the lattice upon relaxation.""",
    epilog="""Author: Ihor Radchenko""",
    )

    args = parser.parse_args()

    drone = VaspToComputedEntryDrone(inc_structure=True, data=["filename", "initial_structure"])
    
    n_cpus = multiprocessing.cpu_count()
    queen = BorgQueen(drone, number_of_drones=n_cpus)
    if n_cpus > 1:
        queen.parallel_assimilate(".")
    else:
        queen.serial_assimilate(".")

    entries = queen.get_data()
    entries = sorted(entries, key=lambda x: x.data["filename"])

    headers = ("Directory", "Formula", "Energy", "E/Atom",
               "% vol chg", "a", "% a chg", "b", "% b chg", "c", "% c chg",
               "alpha", "% alpha chg", "beta", "% beta chg", "gamma", "% gamma chg")

    all_data = []
    for e in entries:
        delta_vol = e.structure.volume / e.data["initial_structure"].volume - 1
        delta_vol = f"{delta_vol * 100:.2f}"
        delta_a = e.structure.lattice.a/e.data['initial_structure'].lattice.a - 1
        delta_a = f"{delta_a * 100:.2f}"
        delta_b = e.structure.lattice.b/e.data['initial_structure'].lattice.b - 1
        delta_b = f"{delta_b * 100:.2f}"
        delta_c = e.structure.lattice.c/e.data['initial_structure'].lattice.c - 1
        delta_c = f"{delta_c * 100:.2f}"
        delta_alpha = e.structure.lattice.alpha/e.data['initial_structure'].lattice.alpha - 1
        delta_alpha = f"{delta_alpha * 100:.2f}"
        delta_beta = e.structure.lattice.beta/e.data['initial_structure'].lattice.beta - 1
        delta_beta = f"{delta_beta * 100:.2f}"
        delta_gamma = e.structure.lattice.gamma/e.data['initial_structure'].lattice.gamma - 1
        delta_gamma = f"{delta_gamma * 100:.2f}"
        all_data.append(
            (
                e.data["filename"].replace("./", ""),
                re.sub(r"\s+", "", e.formula),
                f"{e.energy:.5f}",
                f"{e.energy_per_atom:.5f}",
                delta_vol,
                e.structure.lattice.a, delta_a,
                e.structure.lattice.b, delta_b,
                e.structure.lattice.c, delta_c,
                e.structure.lattice.alpha, delta_alpha,
                e.structure.lattice.beta, delta_beta,
                e.structure.lattice.gamma, delta_gamma
            )
        )

    if len(all_data) > 0:
        print(tabulate(all_data, headers=headers, tablefmt="orgtbl"))
    else:
        print("No valid vasp run found.")
    return 0


if __name__ == "__main__":
    main()
# Scripts:3 ends here
