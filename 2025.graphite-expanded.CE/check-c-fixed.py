#!/usr/bin/env python
"""Check if all the POSCAR files have carbons fixed
and non-carbons fully allowed to relax.
"""
from pathlib import Path
from pymatgen.io.vasp.inputs import Poscar


print('Collecting VASP dirs...')
vasp_dirs = []
# Iterate over all the directories in cwd recursively
# Collect directories containing POSCAR file into vasp_dirs
for path in Path('.').rglob('*'):
    if path.is_dir() and (path / 'POSCAR').is_file():
        vasp_dirs.append(path)
print(f'Collecting VASP dirs... done ({len(vasp_dirs)} found)')

print('Scanning POSCARs...')
for d in vasp_dirs:
    poscar = Poscar.from_file(d / 'POSCAR')
    for site in poscar.structure:
        if site.specie.name == 'C' and site.properties.get('selective_dynamics', None) != [False, False, False]:
            print(f"{poscar} does not have fixed carbon!")
            continue
        if site.specie.name != 'C' and site.properties.get('selective_dynamics', None) != [True, True, True]:
            print(f"{poscar} unexpectedly fixes {site.specie.name}!")
            continue
print('Scanning POSCARs... done')
