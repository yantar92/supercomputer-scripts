#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*calculate band structure for graphite with primitive cell vs. supercell having the same k-point path][calculate band structure for graphite with primitive cell vs. supercell having the same k-point path:1]]
import argparse
from IMDgroup.pymatgen.io.vasp.sets import IMDGraphite

input = IMDGraphite(
    user_incar_settings={
        "SYSTEM": f"graphite",
        "NCORE": 16
    },
    # Force primitive standard cell
    standardize=True)

input.write_input(output_dir='.')
# calculate band structure for graphite with primitive cell vs. supercell having the same k-point path:1 ends here
