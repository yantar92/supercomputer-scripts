#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:1]]
"""Generate VASP input from an existing one with custom functional."""

import warnings
import argparse
import os
import shutil
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

    if args.functional == "PBE":
        vasp_input['INCAR']["GGA"] = "PE"
    elif args.functional == "PBEsol":
        vasp_input['INCAR']["GGA"] = "PS"
    elif args.functional == "PBE+D2":
        vasp_input['INCAR']["IVDW"] = 1
    elif args.functional == "PBE+TS":
        vasp_input['INCAR']["IVDW"] = 2
        vasp_input['INCAR']["PREC"] = 'Accurate'
    elif args.functional == "vdW-DF":
        vasp_input['INCAR']["LASPH"] = True
        vasp_input['INCAR']["GGA"] = "RE"
        vasp_input['INCAR']["AGGAC"] = 0.0
        vasp_input['INCAR']["LUSE_VDW"] = True
    elif args.functional == "vdW-DF2":
        vasp_input['INCAR']["LASPH"] = True
        vasp_input['INCAR']["ZAB_VDW"] = -1.8867
        vasp_input['INCAR']["GGA"] = "ML"
        vasp_input['INCAR']["AGGAC"] = 0.0
        vasp_input['INCAR']["LUSE_VDW"] = True
    elif args.functional == "optB88-vdW":
        vasp_input['INCAR']["LASPH"] = True
        vasp_input['INCAR']["PARAM1"] = 0.18333333
        vasp_input['INCAR']["PARAM2"] = 0.22
        vasp_input['INCAR']["GGA"] = "BO"
        vasp_input['INCAR']["AGGAC"] = 0.0
        vasp_input['INCAR']["LUSE_VDW"] = True
    elif args.functional == "optB86b-vdW":
        vasp_input['INCAR']["LASPH"] = True
        vasp_input['INCAR']["PARAM1"] = 0.1234
        vasp_input['INCAR']["PARAM2"] = 1.0
        vasp_input['INCAR']["GGA"] = "MK"
        vasp_input['INCAR']["AGGAC"] = 0.0
        vasp_input['INCAR']["LUSE_VDW"] = True
    else:
        raise ValueError(f"Unknown functional {args.functional}")

    vasp_input.incar.check_params()
    fix_kpoints(vasp_input.kpoints)
    if "SYSTEM" in vasp_input.incar:
        system_name = vasp_input.incar["SYSTEM"]
    else:
        system_name = "unknown"

    directory=f"{system_name}.{args.functional}"
    vasp_input.write_input(directory)
    if args.functional in ['vdW-DF', 'vdW-DF2', 'optB86b-vdW', 'optB88-vdW']:
        shutil.copy(os.path.join(os.environ['IMDGroup'], 'dist/vdw_kernel.bindat'), directory)


def main() -> None:
    """Main method."""

    parser = argparse.ArgumentParser(
        description="""
    Generate new input files for a custom functional.

    The input files will be placed into <SYSTEM>.<FUNCTIONAL> folder.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "input_directory",
        default=".",
        help="VASP directory to read system"
    )
    parser.add_argument(
        "-f",
        "--functional",
        help="Functional to be used",
        choices=[
            'PBE', 'PBEsol', 'PBE+D2', 'PBE+TS',
            'vdW-DF', 'vdW-DF2',
            'optB88-vdW', 'optB86b-vdW'],
        type=str)

    args = parser.parse_args()

    generate_inputs(args)


if __name__ == "__main__":
    main()
# Scripts:1 ends here
