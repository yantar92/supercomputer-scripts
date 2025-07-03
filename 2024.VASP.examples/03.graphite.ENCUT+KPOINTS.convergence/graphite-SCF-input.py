#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Convergence study of graphite vs. ENCUT and KPOINTS][Convergence study of graphite vs. ENCUT and KPOINTS:2]]
from IMDgroup.pymatgen.io.vasp.sets import IMDGraphite
input = IMDGraphite()
input.write_input(output_dir='.')
# Convergence study of graphite vs. ENCUT and KPOINTS:2 ends here
