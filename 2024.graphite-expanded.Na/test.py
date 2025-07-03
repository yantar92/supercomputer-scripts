#!/bin/env python

import os
import xml
import pymatgen.core as pmg
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.io.vasp.inputs import Poscar
from IMDgroup.pymatgen.cli.imdg_visualize import\
    write_selective_dynamics_summary_maybe
from IMDgroup.pymatgen.core.structure import merge_structures
from IMDgroup.pymatgen.io.vasp.inputs import neb_dirs, nebp

if not nebp('.'):
    raise ValueError("Not in neb dir")

structures = []
for d in neb_dirs('.'):
    if os.path.isfile(os.path.join(d, 'vasprun.xml')):
        try:
            run = Vasprun(os.path.join(d, 'vasprun.xml'))
            structure = run.final_structure
        except xml.etree.ElementTree.ParseError:
            structure = Poscar.from_file(os.path.join(d, 'POSCAR')).structure
    else:
        structure = Poscar.from_file(os.path.join(d, 'POSCAR')).structure
    structures.append(structure)

trajectory = merge_structures(structures)

write_selective_dynamics_summary_maybe(trajectory, 'temp.cif')
