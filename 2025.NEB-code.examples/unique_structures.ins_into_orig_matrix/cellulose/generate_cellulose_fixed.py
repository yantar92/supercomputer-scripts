import os
import pymatgen.core as pmg
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.vasp.outputs import Vasprun

matrix = Poscar.from_file("../../matrix.relaxed/cellulose/cellulose_ibeta.POSCAR").structure

for root, dirs, files in os.walk('../../unique_structures.relaxed/cellulose/02.ins.Zn.fineRELAX.Zn+.unique'):
    for d in dirs:
        if 'run_cellulose' in d:
            struct = Vasprun(os.path.join(root, d, 'vasprun.xml')).final_structure
            Zn_index = struct.species.index(pmg.Element('Zn'))
            Zn_site = struct[Zn_index]
            new_struct = matrix.copy()
            new_struct.append(
                species = Zn_site.species,
                coords = Zn_site.frac_coords,
                coords_are_cartesian=False,
                validate_proximity=True
            )
            new_struct.to_file(f"{d}.cif")
