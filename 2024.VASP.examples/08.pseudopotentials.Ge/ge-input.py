#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:1]]
import warnings
import os
import argparse
from dataclasses import dataclass
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.sets import VaspInputSet
from ase.calculators.vasp.setups import setups_defaults as ase_potential_defaults

@dataclass
class Ge(VaspInputSet):
    """Input set for Ge.
    """
    force_gamma: bool = True  # Must use gamma-centered k-point grid
    CONFIG = {'INCAR':
              {
                  # System name
                  'SYSTEM': "Ge",
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
              'POTCAR': {'Ge': 'Ge'+ase_potential_defaults['recommended']['Ge']}
              }
    def __post_init__(self) -> None:
        with MPRester() as m:
            structure = m.get_structure_by_material_id("mp-32")  # Ge
            assert structure.is_valid()
        self.structure = structure
        super().__post_init__()


parser = argparse.ArgumentParser(
    description="""
    Replace sites in the structure with different atom.

    The input files will be placed into <SYSTEM>.PSEUDO.<species:potential> folder.
    """,
    epilog="""Author: Ihor Radchenko""",
)

parser.add_argument(
    "-p", "--potentials",
    action="append",
    help="Potentials to be insed as Species:Potential atom (e.g. Ge:Ge_d)",
    type=str)

args = parser.parse_args()

potentials = None
if args.potentials is not None:
    potentials = {}
    for strval in args.potentials:
        name, potential = strval.split(':')
        potentials[name] = potential
    args.potentials = potentials

inputset = Ge(user_potcar_settings=args.potentials)

inputset.write_input(
    output_dir=inputset.incar["SYSTEM"]
    + ".PSEUDO." +
    ",".join([f"{name}:{val}" for name, val in args.potentials.items()]))
# Scripts:1 ends here
