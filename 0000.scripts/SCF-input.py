#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts to generate input and run VASP][Scripts to generate input and run VASP:4]]
"""Generate VASP inputs for SCF calculation"""

import argparse
import os
from pymatgen.io.vasp.inputs import VaspInput, Kpoints, Poscar
from custodian.vasp.jobs import VaspJob

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

    if args.use_poscar:
        vasp_input = VaspInput.from_directory(args.input_directory)
    else:
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

    # SCF
    vasp_input['INCAR']['NSW'] = 0
    vasp_input['INCAR']['IBRION'] = -1

    directory=f"{system_name}.SCF"
    vasp_input.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate input files for SCF.

    The input files will be placed into <SYSTEM>.SCF folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )

    parser.add_argument(
        "--use-poscar",
        dest="use_poscar",
        default=False,
        type=bool,
        help="Use POSCAR even when CONTCAR is present.",
    )

    args = parser.parse_args()
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts to generate input and run VASP:4 ends here
