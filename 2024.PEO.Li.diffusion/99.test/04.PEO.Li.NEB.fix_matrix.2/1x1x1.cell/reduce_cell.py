"""Read POSCAR file in current dir, reduce supercell, and write to new.POSCAR
Simply crop the cell + re-add Li applying new boundary conditions.
"""
import pymatgen.core as pmg

str1 = pmg.Structure.from_file('POSCAR')

str2 = pmg.Structure(
    lattice=pmg.Lattice(
        matrix=str1.lattice.matrix / 2.0,
        pbc=str1.lattice.pbc
    ),
    species=str1.species,
    coords=str1.cart_coords,
    coords_are_cartesian=True,
    site_properties=str1.site_properties,
    properties=str1.properties
)

str2 = str2.merge_sites(mode='delete')

for site in str2:
    site.to_unit_cell(in_place=True)

# Group species
str2 = str2.get_sorted_structure(
    key=lambda site: site.species.average_electroneg)

str2.to_file('POSCAR')
