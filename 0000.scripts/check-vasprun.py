#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:2]]
"""Check whether VASP successfully completed."""

import os
import sys
import subprocess
import warnings
from pathlib import Path
from termcolor import colored
from xml.etree.ElementTree import ParseError
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.io.vasp.inputs import Incar


def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    """Print warning in nicer way.
    """
    output = colored(f"{category.__name__}: ", "yellow", attrs=['bold']) + f'{message}'
    print(output, file=file or sys.stderr)


warnings.showwarning = custom_showwarning


def runningp(dir):
    """Is slurm running in DIR?
    """
    result = subprocess.check_output("squeue -u $USER -o %Z | tail -n +2", shell=True).split()
    if dir in [s.decode('utf-8') for s in result]:
        return True
    return False


def main() -> None:
    """Main method."""

    wdir = os.getcwd()
    status = colored("unknown", "red")
    system_name = ""
    if runningp(wdir):
        status = colored("running", "yellow")
        incar = Incar.from_file("INCAR")
        system_name = incar['SYSTEM'] if 'SYSTEM' in incar else "unknown"
    else:
        try:
            run = Vasprun('vasprun.xml', parse_dos=False, parse_eigen=False)
            system_name = run.incar['SYSTEM'] if 'SYSTEM' in run.incar else ""
            status = colored("converged", "green") if run.converged\
                else colored("unconverged", "red")
        except ParseError:
            status = colored("incomplete vasprun.xml", "red")
    print(colored(f"{system_name} {Path(wdir).name}: ", attrs=['bold']) + status)
    return 0
    

if __name__ == "__main__":
    main()
# Scripts:2 ends here
