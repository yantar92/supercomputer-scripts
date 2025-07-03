#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:2]]
"""Generate VASP inputs creating a vacancy in a given structure"""

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

    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"

    # Remove sites
    vasp_input.poscar.structure.remove_sites(args.site_numbers)

    directory=f"{system_name}.vacancy.{','.join(map(str,args.site_numbers))}"
    vasp_input.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Remove sites from structure.

    The input files will be placed into <SYSTEM>.vacancy.<sites> folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    parser.add_argument(
        "-n", "--site-numbers",
        dest="site_numbers",
        action="append",
        help="0-indexed site numbers to be removed (default: 0)",
        type=int)

    args = parser.parse_args()
    if args.site_numbers is None:
        args.site_numbers = [0]
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts:2 ends here
