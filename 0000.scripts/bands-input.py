#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Band structure inputs (!!! fixed k-point path for graphite for now)][Band structure inputs (!!! fixed k-point path for graphite for now):1]]
"""Generate VASP inputs for band calculation"""

import argparse
import os
import shutil
from pymatgen.io.vasp.inputs import VaspInput, Kpoints, Poscar
from pymatgen.io.vasp.outputs import Chgcar
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

    # Set k-point path
    # FIXME: For now, hard coded for graphite
    vasp_input['KPOINTS'] = Kpoints.from_str("""Special k-points for band structure
40  ! intersections 
line-mode
reciprocal
    0.0000000000     0.0000000000     0.0000000000 1    GAMMA
    0.5000000000     0.0000000000     0.0000000000 1    M 


    0.5000000000     0.0000000000     0.0000000000 1    M 
    0.3333333333     0.3333333333     0.0000000000 1    K 


    0.3333333333     0.3333333333     0.0000000000 1    K 
    0.0000000000     0.0000000000     0.0000000000 1    GAMMA


    0.0000000000     0.0000000000     0.0000000000 1    GAMMA
    0.0000000000     0.0000000000     0.5000000000 1    A 


    0.0000000000     0.0000000000     0.5000000000 1    A 
    0.5000000000     0.0000000000     0.5000000000 1    L 


    0.5000000000     0.0000000000     0.5000000000 1    L 
    0.3333333333     0.3333333333     0.5000000000 1    H 


    0.3333333333     0.3333333333     0.5000000000 1    H 
    0.0000000000     0.0000000000     0.5000000000 1    A 


    0.5000000000     0.0000000000     0.5000000000 1    L 
    0.5000000000     0.0000000000     0.0000000000 1    M 


    0.3333333333     0.3333333333     0.5000000000 1    H 
    0.3333333333     0.3333333333     0.0000000000 1    K
        """)

    # band structure calculation
    vasp_input['INCAR']['ICHARG'] = 11

    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"

    directory=f"{system_name}.bands"
    vasp_input.write_input(directory)

    # copy over CHGCAR. Err when does not exist.
    # See https://www.vasp.at/tutorials/latest/bulk/part1/#3-Band-structure-for-face-centered-cubic-silicon-$%5Cuparrow$
    shutil.copy2('CHGCAR', directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate input files for band structure calculation.

    The input files will be placed into <SYSTEM>.bands folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )

    args = parser.parse_args()
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Band structure inputs (!!! fixed k-point path for graphite for now):1 ends here
