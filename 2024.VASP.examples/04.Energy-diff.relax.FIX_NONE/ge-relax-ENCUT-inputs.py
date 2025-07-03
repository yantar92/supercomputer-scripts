#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts to generate input and run VASP][Scripts to generate input and run VASP:3]]
"""This is a master vasp running script to converging ENCUT for a calculation."""

import argparse
import os
import numpy as np
from pymatgen.io.vasp.inputs import VaspInput, Kpoints

IBRION_IONIC_RELAX_CGA = 2
ISIF_RELAX_VOL = ISIF_FIX_POS_SHAPE = 7

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
    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"

    for encut in np.arange(args.encut_min, args.encut_max, args.encut_step):

        directory=f"{system_name}.vc-relax.ENCUT.{encut}"
        current_input = vasp_input.copy()

        vc_relax_overrides = {
            "ISTART": 0,
            "ENCUT": float(encut),
            # Volume relaxation
            "NSW": 100,
            "IBRION": IBRION_IONIC_RELAX_CGA,
            'ISIF': ISIF_RELAX_VOL,
            'EDIFF': 1e-06,
            'EDIFFG': -0.01}

        for key, val in vc_relax_overrides.items():
            current_input['INCAR'][key] = val

        current_input.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate input files for volume convergence study for a given ENCUT range.

    The input files will be placed into <SYSTEM>.vc-relax.ENCUT.<encut value>
    folders.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system to be relaxed"
    )

    parser.add_argument(
        "--encut_min",
        dest="encut_min",
        nargs="?",
        default=100,
        type=float,
        help="Minimal value of ENCUT (default: 300eV)",
    )

    parser.add_argument(
        "--encut_max",
        dest="encut_max",
        nargs="?",
        default=800,
        type=float,
        help="Max value of ENCUT (default: 800eV)",
    )

    parser.add_argument(
        "--encut_step",
        dest="encut_step",
        nargs="?",
        default=50,
        type=float,
        help="ENCUT step (default 50eV)",
    )

    args = parser.parse_args()
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts to generate input and run VASP:3 ends here
