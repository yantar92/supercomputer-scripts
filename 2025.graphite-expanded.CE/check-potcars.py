#!/usr/bin/env python
"""Iterate over POTCAR files and find non-equal POTCARs.
"""
from pathlib import Path
from alive_progress import alive_it
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir

print('Collecting VASP dirs...')
vasp_dirs = []
# Iterate over all the directories in cwd recursively
# Collect directories containing POSCAR file into vasp_dirs
for parent, _, files in Path('.').walk():
    if 'POTCAR' in files:
        vasp_dirs.append(parent)
print(f'Collecting VASP dirs... done ({len(vasp_dirs)} found)')

unique_potcars = []
for d in alive_it(vasp_dirs, enrich_print=False, title="Scanning POTCARs"):
    vaspdir = IMDGVaspDir(d)
    potcar = vaspdir['POTCAR']
    if potcar not in unique_potcars:
        print(f"Found unique POTCAR in {d}")
        unique_potcars.append(potcar)
print('Scanning POTCARs... done')
