#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts to generate input and run VASP][Scripts to generate input and run VASP:2]]
import warnings
import os
from dataclasses import dataclass
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import VaspInputSet
from ase.calculators.vasp.setups import setups_defaults as ase_potential_defaults

# Generate INCAR for Si lattice with Si replaced by Ge

@dataclass
class Si_relax(VaspInputSet):
    """Volume relax input set for Si.
    """
    force_gamma: bool = True  # Must use gamma-centered k-point grid
    CONFIG = {'INCAR':
              {
                  # System name
                  'SYSTEM': "Ge->Si",
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
                  'Si':
                  'Si'+ (ase_potential_defaults['recommended']['Si'] if 'Si' in ase_potential_defaults['recommended'] else "")}
              }
    def __post_init__(self) -> None:
        with MPRester() as m:
            structure = m.get_structure_by_material_id("mp-32")  # Ge
            # Replace Ge with Si
            structure.replace_species({'Ge': 'Si'})
            assert structure.is_valid()
        self.structure = structure
        super().__post_init__()


inputset = Si_relax()
inputset.write_input(output_dir='.')
# Scripts to generate input and run VASP:2 ends here
