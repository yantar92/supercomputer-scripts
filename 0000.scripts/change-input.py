#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:1]]
"""Generate VASP inputs mutating an existing inputs."""

import warnings
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

    vasp_input = VaspInput.from_directory(args.input_directory)

    for key, val in args.incar.items():
        vasp_input['INCAR'][key] = val

    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"


    directory=f"{system_name}.{','.join([f'{key}.{val}' for key, val in args.incar.items()])}"
    vasp_input.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate new input files, setting given parameters.

    The input files will be placed into <SYSTEM>.<PARAM1>.<value>[,<PARAM2>.<vale>,...] folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    parser.add_argument(
        "--incar",
        action="append",
        help="PARAM:VALUE to be set in the INCAR.",
        type=str)

    args = parser.parse_args()
    incar_overrides = {}
    if args.incar is None:
        warnings.warn("No INCAR settings provided.  Creating a copy of the inputs.")
    else:
        for str_val in args.incar:
            key, val = str_val.split(":")
            incar_overrides[key] = val
    args.incar = incar_overrides

    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts:1 ends here
