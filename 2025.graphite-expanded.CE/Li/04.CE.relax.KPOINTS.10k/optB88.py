#!/usr/bin/env python
import sys
from pathlib import Path
import pandas as pd
import pymatgen.core as pmg
from IMDgroup.pymatgen.io.vasp.sets import IMDDerivedInputSet

if not Path('gs.out').is_file():
    print('Cannot find gs.out')
    sys.exit(1)

if not Path('optB88').is_dir():
    Path('optB88').mkdir()

df = pd.read_csv('gs.out', sep=' ', header=None)
for gs_num in df[3]:
    print(f"Processing structure #{gs_num}")
    inputset = IMDDerivedInputSet(
        directory=str(Path(str(gs_num)) / "ATAT"),
        functional="optb88-vdw")
    inputset.write_input(Path('optB88') / Path(f"{str(gs_num)}.optB88"))
