#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Scripts][Scripts:2]]
import warnings
import os
import argparse
from dataclasses import dataclass
from pymatgen.io.vasp.sets import VaspInputSet
from pymatgen.io.vasp.inputs import Kpoints
from ase.calculators.vasp.setups import setups_defaults as ase_potential_defaults
from ase.build import molecule as ase_molecule
from pymatgen.io.ase import AseAtomsAdaptor

@dataclass
class O2(VaspInputSet):
    """Input set for O2.
    """
    force_gamma: bool = True  # Must use gamma-centered k-point grid
    CONFIG = {'INCAR':
              {
                  # System name
                  'SYSTEM': "O2",
                  # Electronic minimization algo
                  'ALGO': 'Normal',
                  # Energy cutoff
                  'ENCUT': 550.0,  # energy cutoff
                  # Smearing
                  'ISMEAR': -5, # as recommended for total energy calculations in non-metals in https://www.vasp.at/wiki/index.php/ISMEAR
                  'SIGMA': 0.01,
                  'ISPIN': 2, # magnetic, but !!! not spin up + down
                  # FIXME: May we calculate it automatically, from POTCAR + INCAR data?
                  'NCORE': 16 },
              'KPOINTS': { 'grid_density': 1 }, # force 1x1x1 grid
              'POTCAR_FUNCTIONAL': 'PBE_64',
              'POTCAR': {'O': 'O'}
              }
    def __post_init__(self) -> None:
        o2_ase = ase_molecule('O2')
        o2 = AseAtomsAdaptor.get_molecule(o2_ase)
        self.structure = o2.get_boxed_structure(20, 20, 20) # 20 ans
        super().__post_init__()


parser = argparse.ArgumentParser(
    description="""Generate O2 inputs.""",
    epilog="""Author: Ihor Radchenko""",
)

inputset = O2()

inputset.write_input(output_dir=".")
# Scripts:2 ends here
