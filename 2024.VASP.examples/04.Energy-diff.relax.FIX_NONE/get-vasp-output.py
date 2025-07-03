#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts to generate input and run VASP][Scripts to generate input and run VASP:5]]
"""Read ENCUT, energy_per_atom, and lattice parameter from VASP output.
"""
import os
import argparse
from pymatgen.io.vasp.outputs import Vasprun

def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Read ENCUT, energy per atom, and lattice paramter from VASP output.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read output from"
    )

    args = parser.parse_args()

    v = Vasprun(os.path.join(args.input_directory, "vasprun.xml"))
    encut = v.incar["ENCUT"]
    e_per_atom = v.final_energy / len(v.final_structure)
    # The last structure in the ionic relaxation
    lattice_parameter = v.final_structure.lattice.abc[0]
    
    print(f'{encut}\t{e_per_atom}\t{lattice_parameter}')


if __name__ == "__main__":
    main()
# Scripts to generate input and run VASP:5 ends here
