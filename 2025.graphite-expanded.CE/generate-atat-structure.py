"""This script takes POSCAR with max concentration as input and generates
a number of structures with a given concentration instead. The generated structures
are saved in 0XXXX/str.out files to be used by ATAT.
Scripts takes the following arguments:
generate-atat-structure.py </path/to/POSCAR> <ion_name> <concentration> [n_structures]
"""
import argparse
import os
from pathlib import Path

from IMDgroup.pymatgen.core.structure import IMDStructure
from pymatgen.transformations.advanced_transformations import EnumerateStructureTransformation

# Parse command-line arguments
parser = argparse.ArgumentParser(description='Generate ATAT structures with specified concentration')
parser.add_argument('poscar', type=str, help='Path to POSCAR file')
parser.add_argument('ion_name', type=str, help='Name of ion to adjust concentration')
parser.add_argument('concentration', type=float, help='Target concentration (0-1)')
parser.add_argument('-n', '--n_structures', type=int, default=10, help='Number of structures to generate (default: 10)')
args = parser.parse_args()

# Read structure and replace species
structure = IMDStructure.from_file(args.poscar)
structure.replace_species({
    args.ion_name: {
        args.ion_name: args.concentration,
        'X': 1 - args.concentration  # Vacancies represented as X
    }
})

# Generate structures
transformation = EnumerateStructureTransformation(
    max_cell_size=None,
    max_disordered_sites=400
)
structs = transformation.apply_transformation(structure, return_ranked_list=args.n_structures)

# Create directories and write structures
dir_names = []
for s in structs:
    counter = 0
    while True:
        dir_name = f"{counter:04d}"
        if not os.path.exists(dir_name):
            break
        counter += 1
    os.makedirs(dir_name)
    dir_names.append(dir_name)
    s['structure'].to_file(Path(dir_name) / "str.out", fmt="atat")

print(f"Generated {len(structs)} structures in {dir_names} directories")
