import os
from IMDgroup.pymatgen.core.structure import merge_structures
import pymatgen.core as pmg
structs = []
for wdir, subdirs, _ in os.walk('.'):
    if os.path.isfile(os.path.join(wdir, "POSCAR")):
        structs.append(pmg.Structure.from_file(os.path.join(wdir, "POSCAR")))
merged = merge_structures(structs)
merged.to_file("summary.cif")
