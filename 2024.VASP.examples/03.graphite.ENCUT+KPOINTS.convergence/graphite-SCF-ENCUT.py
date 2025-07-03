#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Convergence study of graphite vs. ENCUT and KPOINTS][Convergence study of graphite vs. ENCUT and KPOINTS:3]]
"""This is a master vasp running script to converging ENCUT for a calculation."""

import logging

from pymatgen.io.vasp.inputs import VaspInput
from pymatgen.io.vasp.outputs import Vasprun

from custodian.custodian import Custodian
from custodian.vasp.handlers import UnconvergedErrorHandler, VaspErrorHandler
from custodian.vasp.jobs import VaspJob

FORMAT = "%(asctime)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.INFO, filename="run.log")


def get_runs(vasp_command, target=1e-4, max_steps=20, encut0=550):
    """Generate the runs using a generator until convergence is achieved."""
    energy = 0
    vasp_input = VaspInput.from_directory(".")
    encut_step = 50
    
    for step in range(max_steps):
        encut = encut0 + step * encut_step
        if step == 0:
            settings = [ {"dict": "INCAR", "action": {"_set": {"ENCUT": encut0}}}]
            backup = True
        else:
            backup = False
            v = Vasprun("vasprun.xml")
            e_per_atom = v.final_energy / len(v.final_structure)
            logging.info(f"ENCUT = {v.incar['ENCUT']} Current energy is {e_per_atom} eV/atom")
            ediff = abs(e_per_atom - energy)
            if ediff < target:
                logging.info(f"Converged to {ediff} eV/atom!")
                break
            logging.info(f"Not yet converged; dE {ediff} eV/atom!")
            energy = e_per_atom
            settings = [
                {
                    "dict": "INCAR",
                    "action": {"_set": {"ISTART": 1, "ENCUT": encut}}
                },
                {
                    "file": "CONTCAR",
                    "action": {"_file_copy": {"dest": "POSCAR"}},
                },
            ]
        yield VaspJob(
            vasp_command,
            final=False,
            backup=backup,
            suffix=f".ENCUT.{encut}",
            settings_override=settings,
            auto_npar=True
        )


def do_run(args) -> None:
    """Perform the run."""
    handlers = [VaspErrorHandler(), UnconvergedErrorHandler()]
    c = Custodian(
        handlers,
        get_runs(
            vasp_command=args.command.split(),
            target=args.target,
            max_steps=args.max_steps,
            encut0=args.encut0
        ),
        max_errors=10,
    )
    c.run()


def main() -> None:
    """Main method."""
    import argparse

    parser = argparse.ArgumentParser(
        description="""
    perform ENCUT convergence.  The default convergence criteria is
    1meV/atom, but this can be set using the --target option.
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
        "-m",
        "--max_steps",
        dest="max_steps",
        nargs="?",
        default=20,
        type=int,
        help="The maximum number of increment steps. This puts an "
        "upper bound on the largest ENCUT attempted.",
    )

    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        nargs="?",
        default=1e-4,
        type=float,
        help="The target converge in energy per atom to achieve "
        "convergence. E.g., 1e-4 means the ENCUT will be increased "
        "until a converged of 1meV is reached.",
    )

    parser.add_argument(
        "-e",
        "--encut0",
        dest="encut0",
        nargs="?",
        default=550,
        type=float,
        help="The initial value of ENCUT"
    )

    args = parser.parse_args()
    do_run(args)


if __name__ == "__main__":
    main()
# Convergence study of graphite vs. ENCUT and KPOINTS:3 ends here
