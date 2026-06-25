#!/usr/bin/env python
# Read POSCAR file using pymatgen library and store it as Structure object.
# Then, scale the structure to 2x2x2 supercell
# Then, find all Na atoms in the structure and delete Na atoms that are closer than 1.5 times their sum of atomic radiuses
# Delete the atoms one by one, restarting the process after each deletion

from pymatgen.core import Structure
from pymatgen.core.periodic_table import Element

# Load structure from POSCAR
struct = Structure.from_file("POSCAR.old")

struct.make_supercell([1, 1, 1])

# Get Li covalent radius
r_li = Element("Li").atomic_radius
threshold = 1.1 * (r_li + r_li)

# Process Na atoms
while True:
    na_sites = [i for i, site in enumerate(struct) if site.species_string == "Li"]
    found = False
    
    for i in range(len(na_sites)):
        for j in range(i+1, len(na_sites)):
            idx1, idx2 = na_sites[i], na_sites[j]
            if struct.get_distance(idx1, idx2) < threshold:
                struct.remove_sites([max(idx1, idx2)])  # Remove higher-index atom
                found = True
                break
        if found:
            break
    
    if not found:
        break

from IMDgroup.pymatgen.core.structure import reduce_supercell
struct_red = reduce_supercell(struct)

# Save modified structure
print(f"{len(struct)} -> {len(struct_red)}")
struct_red.to("POSCAR")
