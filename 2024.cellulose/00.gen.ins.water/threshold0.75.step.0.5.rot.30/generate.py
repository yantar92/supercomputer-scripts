import logging
import numpy as np
import pymatgen.core as pmg
from IMDgroup.pymatgen.transformations.insert_molecule\
    import InsertMoleculeTransformation

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

transformer = InsertMoleculeTransformation(
    'water.xyz',
    step=0.5, multithread=True, anglestep=np.radians(30),
    proximity_threshold=0.75)
structures = transformer.all_inserts('cellulose_ibeta.POSCAR')

for idx, structure in enumerate(structures):
    structure.to_file(f'cellulose_ibeta_water_{idx:03d}.POSCAR')
