#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Inputs][Inputs:3]]
"""Generate VASP inputs for vc-relax calculation"""

import argparse
import os
from pymatgen.io.vasp.inputs import VaspInput, Kpoints, Poscar
from custodian.vasp.jobs import VaspJob

ISIF_RELAX_POS = ISIF_FIX_SHAPE_VOL = 2
ISIF_RELAX_POS_SHAPE_VOL = ISIF_FIX_NONE = 3
ISIF_RELAX_POS_SHAPE = ISIF_FIX_VOL = 4
ISIF_RELAX_SHAPE = IFIX_FIX_POS_VOL = 5
ISIF_RELAX_SHAPE_VOL = ISIF_FIX_POS = 6
ISIF_RELAX_VOL = ISIF_FIX_POS_SHAPE = 7
ISIF_RELAX_POS_VOL = ISIF_FIX_SHAPE = 8


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

    # vc-relax
    IBRION_IONIC_RELAX_CGA = 2
    ISIF_RELAX_VOL = ISIF_FIX_POS_SHAPE = 7
    vc_relax_overrides = {
        "ISTART": 0,
        # Volume relaxation
        "NSW": 100,
        "IBRION": IBRION_IONIC_RELAX_CGA,
        'ISIF': globals()["ISIF_" + args.isif],
        'EDIFF': 1e-06,
        'EDIFFG': -0.01}

    for key, val in vc_relax_overrides.items():
        vasp_input['INCAR'][key] = val
        
    directory=f"{system_name}.relax.{args.isif}"
    vasp_input.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate input files for vc-relax.

    The input files will be placed into <SYSTEM>.relax.<ISIF constraint> folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    parser.add_argument(
        "--isif",
        help="""Relaxation type (default: RELAX_VOL)
Can be one of:
- RELAX_POS, FIX_SHAPE_VOL
- RELAX_POS_SHAPE_VOL, FIX_NONE
- RELAX_POS_SHAPE, FIX_VOL
- RELAX_SHAPE, FIX_POS_VOL
- RELAX_SHAPE_VOL, FIX_POS
- RELAX_VOL, FIX_POS_SHAPE
- RELAX_POS_VOL, FIX_SHAPE
""",
        default="RELAX_VOL")

    args = parser.parse_args()
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Inputs:3 ends here
