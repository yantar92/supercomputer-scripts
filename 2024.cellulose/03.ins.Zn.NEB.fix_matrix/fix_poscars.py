# This script is here because I ran into pymatgen writing POSCAR files
# with duplicate species:
# https://github.com/materialsproject/pymatgen/issues/1633
# The script manually fixes the POSCAR files
# Newer versions of imdg script will take care about this automatically.
import warnings
import os
from pymatgen.io.vasp.outputs import Poscar

if os.path.isfile('POSCAR'):
    poscar = Poscar.from_file('POSCAR')
    structure = poscar.structure.get_sorted_structure(
        key=lambda site: site.species.average_electroneg)
    fixed_poscar = Poscar(structure)
    fixed_poscar.write_file('POSCAR')
else:
    warnings.warn(
        f"No POSCAR found in {os.getcwd()}"
    )
