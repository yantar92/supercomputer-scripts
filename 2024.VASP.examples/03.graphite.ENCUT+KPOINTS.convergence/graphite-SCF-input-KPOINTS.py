#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Convergence study of graphite vs. ENCUT and KPOINTS][Convergence study of graphite vs. ENCUT and KPOINTS:5]]
from IMDgroup.pymatgen.io.vasp.sets import IMDGraphite
input = IMDGraphite(user_kpoints_settings={"grid_density": 100}, user_incar_settings={"ENCUT": 1000})
input.write_input(output_dir='.')
# Convergence study of graphite vs. ENCUT and KPOINTS:5 ends here
