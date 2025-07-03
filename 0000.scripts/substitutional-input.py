#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:2]]
"""Generate VASP inputs creating a substitution in a given structure"""

import argparse
import os
from pymatgen.io.vasp.inputs import VaspInput, Kpoints, Poscar
import pymatgen.core as pmg

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

    # Replace sites
    for idx, name in args.substitutions:
        vasp_input.poscar.structure.replace(idx, name)
    # Apparently our gorun (ase?) cannot handle POTCAR generation for
    # repeating species
    vasp_input.poscar.structure.sort()

    # FIXME: We do not update POTCAR here, relying upon gorun
    # auto-genrating appropriate POTCAR
    vasp_input['POTCAR'] = None

    directory=f"{system_name}.subst.{','.join([f'{idx}:{name}' for idx, name in args.substitutions])}"
    vasp_input.write_input(directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Replace sites in the structure with different atom.

    The input files will be placed into <SYSTEM>.subst.<sites:replacements> folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    parser.add_argument(
        "-S", "--substitutions",
        action="append",
        help="Substituionas in the format site number:new atom (e.g. 0:Ni)",
        type=str)

    args = parser.parse_args()
    substitutions = []
    for strval in args.substitutions:
        idx, name = strval.split(':')
        substitutions.append((int(idx), name))
    args.substitutions = substitutions
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts:2 ends here
