#!/usr/bin/env python
import sys
from pathlib import Path
import pandas as pd
import pymatgen.core as pmg
from IMDgroup.pymatgen.io.vasp.sets import IMDDerivedInputSet

if not Path('gs.out').is_file():
    print('Cannot find gs.out')
    sys.exit(1)

if not Path('_relax').is_dir():
    Path('_relax').mkdir()

df = pd.read_csv('gs.out', sep=' ', header=None)
FIX = [False] * 3
NOFIX = [True] * 3
for gs_num in df[3]:
    print(f"Processing structure #{gs_num}")
    inputset = IMDDerivedInputSet(directory=str(Path(str(gs_num)) / "ATAT"))
    structure = inputset.structure
    assert isinstance(structure, pmg.Structure)
    structure.add_site_property(
        'selective_dynamics',
        [FIX if site.specie.name == 'C' else NOFIX
         for site in structure],
    )
    inputset.structure = structure
    inputset.write_input(Path('_relax') / Path(f"{str(gs_num)}.relax"))
