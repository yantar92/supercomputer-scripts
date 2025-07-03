"""In current NEB directory, compute structure distance betwee images (use CONTCARS, if available).
"""

from pathlib import Path
import pymatgen.core as pmg
from IMDgroup.pymatgen.core.structure import structure_distance
from IMDgroup.pymatgen.io.vasp.inputs import nebp, neb_dirs

if not nebp("./"):
    raise RuntimeError("Current directory is not a NEB directory")

cur_dir = Path(".")
structures = []
structures_initial = []
for p in neb_dirs(cur_dir):
    contcar = Path(p) / "CONTCAR"
    poscar = Path(p) / "POSCAR"
    contcar_struct = None
    if contcar.is_file():
        contcar_struct = pmg.Structure.from_file(contcar)
    poscar_struct = pmg.Structure.from_file(poscar)
    poscar_struct.properties['origin_path'] = p
    if contcar_struct is not None:
        contcar_struct.properties['origin_path'] = p
        structures.append(contcar_struct)
    else:
        structures.append(poscar_struct)
    structures_initial.append(poscar_struct)

def print_structure_diffs(structures):
    for str1, str2 in zip(structures, structures[1:]):
        str1_path = str1.properties['origin_path']
        str2_path = str2.properties['origin_path']
        print(f"{str1_path} -> {str2_path}: {structure_distance(str1, str2)}")

print(f"Initial distances between NEB images:")
print_structure_diffs(structures_initial)
print(f"Final distances between NEB images:")
print_structure_diffs(structures)
