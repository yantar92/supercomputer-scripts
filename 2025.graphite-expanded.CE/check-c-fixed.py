#!/usr/bin/env python
"""Check if all the POSCAR files have carbons fixed
and non-carbons fully allowed to relax.
"""
from pathlib import Path
from pymatgen.io.vasp.inputs import Poscar
from alive_progress import alive_it
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir


print('Collecting VASP dirs...')
vasp_dirs = []
# Iterate over all the directories in cwd recursively
# Collect directories containing POSCAR file into vasp_dirs
for parent, _, files in Path('.').walk():
    if 'POSCAR' in files:
        vasp_dirs.append(parent)
print(f'Collecting VASP dirs... done ({len(vasp_dirs)} found)')

for d in alive_it(vasp_dirs, enrich_print=False, title="Scanning POSCARs"):
    vaspdir = IMDGVaspDir(d)
    poscar = vaspdir['POSCAR']
    if poscar is None:
        continue
    for site in poscar.structure:
        if site.specie.name == 'C' and list(site.properties.get('selective_dynamics', [1, 1, 1])) != [False, False, False]:
            print(f"{d / 'POSCAR'} does not have fixed carbon!")
            break
        if site.specie.name != 'C' and list(site.properties.get('selective_dynamics', [1, 1, 1])) != [True, True, True]:
            print(f"{d / 'POSCAR'} unexpectedly fixes {site.specie.name}!")
            break
print('Scanning POSCARs... done')
