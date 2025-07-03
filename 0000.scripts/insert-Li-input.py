#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:1]]
"""Generate VASP input inserting atom into VASP output."""

import warnings
import argparse
import os
import shutil
import numpy as np
from pymatgen.io.vasp.inputs import VaspInput, Kpoints, Poscar
from IMDgroup.pymatgen.transformations import InsertMoleculeTransformation

def fix_kpoints(kpoints) -> None:
    """Make sure that K-points grid does not use floats.
    pymatgen forces k-point grid to be floats, which cannot be read by
    some VASP versions (compiled with GNU toolchain).
    Modify KPOINTS by side effect.
    """
    kpts_copy = kpoints.kpts
    for idx, ln in enumerate(kpts_copy):
        a, b, c = ln
        ln_int = (int(a), int(b), int(c))
        if ln_int == ln:
            kpts_copy[idx] = ln_int
    # We need this because kpts is not editable by index.
    kpoints.kpts = kpts_copy


def generate_inputs(args) -> None:
    """Generate a set of VASP inputs."""

    # This will raise an error when CONTCAR is not present.
    # We do it on purpose to make sure that relaxation run has been performed
    vasp_input = VaspInput.from_directory(
        args.input_directory, {"CONTCAR": Poscar})
    # Copy over CONTCAR to POSCAR
    vasp_input['POSCAR'] = vasp_input['CONTCAR']

    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"

    transformer = InsertMoleculeTransformation("Li", step=0.5)
    structures = transformer.all_inserts(
        vasp_input['POSCAR'].structure,
        limit=args.limit)

    for idx, structure in enumerate(structures):
        directory=f"{system_name}.ins.Li.{idx}"
        vasp_input2 = vasp_input.copy()
        vasp_input2['POSCAR'] = Poscar(structure)
        vasp_input2.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate new input files with Li atom inserted into CONTCAR structure.

    The input files will be placed into <SYSTEM>.ins.Li.<idx> folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    parser.add_argument(
        "--limit",
        help="Number of structures (negative to randomize search)",
        type=int)

    args = parser.parse_args()

    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts:1 ends here
