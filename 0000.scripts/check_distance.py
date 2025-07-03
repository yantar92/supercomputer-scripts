#!/usr/bin/env python
import pymatgen.core as pmg
import numpy as np
import sys
import warnings
from pathlib import Path
from IMDgroup.pymatgen.core.structure import structure_is_valid2


for subdir in Path(".").iterdir():
    if subdir.is_dir():
        contcar = subdir / 'CONTCAR.relax'
        if not contcar.exists():
            continue
        print(subdir)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            s = pmg.Structure.from_file(subdir / 'CONTCAR.relax')

        if not structure_is_valid2(s, frac_tol=0.5):
            print("Too close!")
            Path(subdir / 'terminal_error').touch()
