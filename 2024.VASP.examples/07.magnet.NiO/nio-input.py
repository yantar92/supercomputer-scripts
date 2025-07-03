#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:1]]
import warnings
import os
from dataclasses import dataclass
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import VaspInputSet
from ase.calculators.vasp.setups import setups_defaults as ase_potential_defaults

@dataclass
class NiO(VaspInputSet):
    """Input set for NiO.
    """
    force_gamma: bool = True  # Must use gamma-centered k-point grid
    CONFIG = {'INCAR':
              {
                  # System name
                  'SYSTEM': "NiO",
                  # Electronic minimization algo
                  'ALGO': 'Normal',
                  # Energy cutoff
                  'ENCUT': 550.0,  # energy cutoff
                  # Smearing
                  'ISMEAR': -5, # as recommended for total energy calculations in non-metals in https://www.vasp.at/wiki/index.php/ISMEAR
                  'SIGMA': 0.01,
                  # FIXME: May we calculate it automatically, from POTCAR + INCAR data?
                  'NCORE': 16
              },
              'KPOINTS': { 'grid_density': 5000 },
              'POTCAR_FUNCTIONAL': 'PBE_64',
              'POTCAR': {
                  'Ni':
                  'Ni'+ (ase_potential_defaults['recommended']['Si'] if 'Si' in ase_potential_defaults['recommended'] else ""),
                  'O':
                  'O'+ (ase_potential_defaults['recommended']['O'] if 'O' in ase_potential_defaults['recommended'] else ""),}
              }
    def __post_init__(self) -> None:
        with MPRester() as m:
            structure = m.get_structure_by_material_id("mp-19009")  # NiO
            assert structure.is_valid()
        self.structure = structure
        super().__post_init__()


inputset = NiO()
inputset.write_input(output_dir='.')
# Scripts:1 ends here
