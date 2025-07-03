#!/usr/bin/env python
import os
from pathlib import Path 
from pymatgen.io.vasp.outputs import Vasprun

for root, dirs, files in os.walk('.'):
    if 'ATAT.SCF' in dirs:
        # print(f"Checking {root}")
        try:
            run = Vasprun(Path(root) / 'ATAT.SCF' / 'vasprun.xml')
        except Exception as e:
            print(f"---- Parser error in {root}")
            Path(Path(root) / 'error').touch()
            continue
        if run.converged:
            Path(Path(root) / 'energy').write_text(f"{float(run.final_energy)}\n")
        else:
            print(f"---- Error in {root}")
            Path(Path(root) / 'error').touch()
