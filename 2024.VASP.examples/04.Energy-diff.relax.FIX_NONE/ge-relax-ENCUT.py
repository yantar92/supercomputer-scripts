#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts to generate input and run VASP][Scripts to generate input and run VASP:6]]
"""This is a master vasp running script to converging ENCUT for a calculation."""

import warnings
import os
import logging
import shutil
from dataclasses import dataclass

from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import VaspInputSet
from pymatgen.io.vasp.inputs import VaspInput
from pymatgen.io.vasp.outputs import Vasprun
from custodian.custodian import Custodian
from custodian.vasp.handlers import UnconvergedErrorHandler, VaspErrorHandler
from custodian.vasp.jobs import VaspJob

FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO, filename="run.log")

# Generate INCAR for volume relaxation
IBRION_IONIC_RELAX_CGA = 2
ISIF_RELAX_VOL = ISIF_FIX_POS_SHAPE = 7



def do_run(args) -> None:
    """Perform the run."""

    working_dir = os.getcwd()
    # This does not work on Helios - pymatgen unconditionally converts
    # Kpoint grid values to floats: (e.g. 13.0 13.0 13.0).  But our
    # VASP comiled with GNU toolchain cannot read floating point
    # values like this.
    # vasp_input = VaspInput.from_directory(".")

    handlers = [VaspErrorHandler(), UnconvergedErrorHandler()]
    vasp_command = args.command.split()
    output = args.output

    with open(output, 'w') as f:
        f.write("# ENCUT, eV\tEnergy, eV/atom\tLattice constant, Å\n")

    def _copy_VASP_to(directory):
        """Copy VASP inputs from current dir to DIRECTORY."""
        input_files = [os.path.join(os.getcwd(), f)
                       for f in ["INCAR", "KPOINTS", "POSCAR", "POTCAR"]]
        if not os.path.isdir(directory):
            os.makedirs(directory)
        for f in input_files:
            shutil.copy(f, directory)
        # vasp_input.write_input(output_dir=directory)


    for encut in range(args.encut_min, args.encut_max, args.encut_step):

        logging.info("Starting jobs for ENCUT = %f", encut)
        directory=f"Ge.vc-relax.ENCUT.{encut}"

        _copy_VASP_to(directory)
        # In theory, Custodian should be able to handle passing
        # working dir, but it failed to work in my tests
        # Changing working dir by force - Custodian does work with
        # inputs being in current directory
        os.chdir(directory)

        vc_relax_cmd = VaspJob(
            vasp_command,
            final=False,
            backup=False,
            settings_override=[
                {"dict": "INCAR",
                 "action":
                 {"_set": {"ISTART": 0,
                           "ENCUT": encut,
                           # Volume relaxation
                           "NSW": 100,
                           "IBRION": IBRION_IONIC_RELAX_CGA,
                           'ISIF': ISIF_RELAX_VOL,
                           'EDIFF': 1e-06,
                           'EDIFFG': -0.01}}},
            ],
            auto_npar=True
        )

        c = Custodian(handlers, [vc_relax_cmd], max_errors=10)
        c.run()

        v_vc = Vasprun("vasprun.xml")
        e_per_atom_vc_relax = v_vc.final_energy / len(v_vc.final_structure)
        # The last structure in the ionic relaxation
        lattice_parameter = v_vc.final_structure.lattice.abc[0]

        scf_directory = directory + ".SCF"
        # Working dir is the vc_relax dir now.  Create nested dir.
        _copy_VASP_to(scf_directory)
        os.chdir(scf_directory)

        scf_cmd = VaspJob(
            vasp_command,
            final=True,
            backup=True,
            settings_override=[
                {"file": "CONTCAR", "action": {"_file_copy": {"dest": "POSCAR"}}},
                {"dict": "INCAR", "action": {"_set": {"NSW": 0, "IBRION": -1}}},
            ],
            auto_npar=True
        )

        c = Custodian(handlers, [scf_cmd], max_errors=10)
        c.run()

        v_scf = Vasprun("vasprun.xml")
        e_per_atom_scf = v.final_energy / len(v.final_structure)

        os.chdir(working_dir)

        logging.info(
            "ENCUT = %f Current energy is %f (%f) eV/atom Lattice constant is %f Å",
            v.incar['ENCUT'], e_per_atom_scf, e_per_atom_vc_relax, lattice_parameter)

        with open(output, 'a') as f:
            f.write(f'{v.incar["ENCUT"]}\t{e_per_atom}\t{lattice_parameter}\n')


def main() -> None:
    """Main method."""
    import argparse

    parser = argparse.ArgumentParser(
        description="""
    perform volume convergence study for a given ENCUT range.
    Assume the structure to be relaxes is in current directory.
    """,
    epilog="""Author: Ihor Radchenko""",
    )

    parser.add_argument(
        "-c",
        "--command",
        dest="command",
        nargs="?",
        default="mpiexec vasp_ncl",
        type=str,
        help="VASP command. Defaults to 'mpiexec vasp_ncl'.",
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

    parser.add_argument(
        "--output",
        dest="output",
        nargs="?",
        default="convergence.txt",
        type=str,
        help="Output file for convergence data (default: convergence.txt)",
    )

    args = parser.parse_args()
    do_run(args)


if __name__ == "__main__":
    main()
# Scripts to generate input and run VASP:6 ends here
