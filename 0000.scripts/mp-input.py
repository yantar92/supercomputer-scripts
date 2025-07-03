#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::mp-input.py][mp-input.py]]
import warnings
import os
import argparse
from dataclasses import dataclass
from pymatgen.ext.matproj import MPRester
from pymatgen.symmetry.analyzer import SpacegroupAnalyzer
from pymatgen.io.vasp.sets import VaspInputSet
import pymatgen.core as pmg
from ase.calculators.vasp.setups import setups_defaults as ase_potential_defaults

# ase uses pairs of 'Si': '_suffix'.  Convert them into 'Si': 'Si_suffix'
POTCAR_RECOMMENDED = dict(
    (name, name + suffix)
    for name, suffix in ase_potential_defaults['recommended'].items())

@dataclass
class IMDDefaultInputSet(VaspInputSet):
    """Default input set for IMDGroup.
    """
    
    CONFIG = {'INCAR':
              {
                  # Generic INCAR defaults independes from a given system
                  # Electronic minimization algo
                  'ALGO': 'Normal',
                  # Energy cutoff
                  'ENCUT': 550.0,  # energy cutoff
                  # Smearing, defaults suggested in https://www.vasp.at/wiki/index.php/ISMEAR
                  'ISMEAR': 0,
                  'SIGMA': 0.04,
                  # FIXME: May we calculate it automatically, from POTCAR + INCAR data?
                  'NCORE': 16
              },
              'KPOINTS': { 'grid_density': 10000 },
              'POTCAR_FUNCTIONAL': 'PBE_64',
              'POTCAR': POTCAR_RECOMMENDED}
    def __post_init__(self) -> None:
        assert self.structure.is_valid()

        # Setup default POTCAR.  If an element is missing from
        # POTCAR_RECOMMENED, assume that the potential name is the
        # same with element name.
        for element in self.structure.composition.elements:
            if element.symbol not in self.CONFIG['POTCAR']:
                self.CONFIG['POTCAR'][element.symbol] = element.symbol

        formula = self.structure.reduced_formula
        lattice_type = SpacegroupAnalyzer(self.structure).get_crystal_system()
        space_group = SpacegroupAnalyzer(self.structure).get_space_group_number()

        self.CONFIG['INCAR']['SYSTEM'] = f'{formula}.{self.structure.properties["mpid"]}.{lattice_type}.{space_group}'
        super().__post_init__()


parser = argparse.ArgumentParser(
    description="""
    Generate inputs for a given Materials Project structure ID.

        The input files will be placed into <FORMULA>.<ID>.<SYMMETRY> folder.
        """,
        epilog="""Author: Ihor Radchenko""",
)

parser.add_argument("mpid",
    help="Materials Project ID (e.g. mp-149 for Si)",
    type=str)

args = parser.parse_args()
structure = pmg.Structure.from_id(args.mpid)
# Sometimes, Materials Project does not return standardized structure
# Force it
analyzer = SpacegroupAnalyzer(structure)
structure = analyzer.get_primitive_standard_structure()
structure.properties['mpid'] = args.mpid
print(structure)
inputset = IMDDefaultInputSet(structure)
inputset.write_input(output_dir=inputset.incar['SYSTEM'])
# mp-input.py ends here
