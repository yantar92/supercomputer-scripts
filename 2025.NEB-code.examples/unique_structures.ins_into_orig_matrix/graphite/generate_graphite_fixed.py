import os
import pymatgen.core as pmg
from pymatgen.io.vasp.outputs import Vasprun

matrix = Vasprun("../../matrix.relaxed/graphite/graphite.AB.pure/strain.c.0.00/vasprun.xml").final_structure

for root, dirs, files in os.walk('../../unique_structures.relaxed/graphite/graphite.AB.Na/strain.c.0.00/'):
    for d in dirs:
        if 'AB' in d:
            struct = Vasprun(os.path.join(root, d, 'vasprun.xml')).final_structure
            Na_index = struct.species.index(pmg.Element('Na'))
            Na_site = struct[Na_index]
            new_struct = matrix.copy()
            new_struct.append(
                species = Na_site.species,
                coords = Na_site.frac_coords,
                coords_are_cartesian=False,
                validate_proximity=True
            )
            new_struct.to_file(f"{d}.cif")
