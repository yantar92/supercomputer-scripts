import os
import pymatgen.core as pmg
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.vasp.outputs import Vasprun

matrix = Poscar.from_file("../../matrix.relaxed/PEO/CONTCAR").structure

for root, dirs, files in os.walk('../../unique_structures.relaxed/PEO/'):
    for d in dirs:
        if 'ins.Li' in d:
            struct = Vasprun(os.path.join(root, d, 'vasprun.xml')).final_structure
            Li_index = struct.species.index(pmg.Element('Li'))
            Li_site = struct[Li_index]
            new_struct = matrix.copy()
            new_struct.append(
                species = Li_site.species,
                coords = Li_site.frac_coords,
                coords_are_cartesian=False,
                validate_proximity=True
            )
            new_struct.to_file(f"{d}.cif")
