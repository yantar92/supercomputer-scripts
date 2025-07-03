import pymatgen.core as pmg
s = pmg.Structure.from_file('POSCAR')

s.add_site_property("selective_dynamics", [[False, False, False] if site.specie == pmg.Element('Li') else [True, True, True] for site in s])
s.to_file('POSCAR')
