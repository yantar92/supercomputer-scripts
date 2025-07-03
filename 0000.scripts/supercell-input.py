#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Inputs][Inputs:2]]
import argparse
import os
from pymatgen.io.vasp.inputs import VaspInput, Kpoints, Poscar


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

    # supercell: N1xN2xN3 string
    scaling = [int(x) for x in args.supercell.split("x")]

    vasp_input = VaspInput.from_directory(args.input_directory)

    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"
    system_name = f"{system_name}.{args.supercell}"

    vasp_input.poscar.structure.make_supercell(scaling)

    vasp_input.write_input(system_name)


def main() -> None:
    """Main method."""


    parser = argparse.ArgumentParser(description="Generate graphite VASP input.")
    parser.add_argument(
        "-s", "--supercell",
        help="Supercell size (default: 1x1x1)",
        default="1x1x1")
    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    args = parser.parse_args()
    generate_inputs(args)


if __name__ == "__main__":
    main()
# Inputs:2 ends here
