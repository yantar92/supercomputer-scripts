#!/usr/bin/env python
from multiprocessing import Pool
from IMDgroup.pymatgen.transformations.symmetry_clone import SymmetryCloneTransformation
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.analysis.structure_matcher import StructureMatcher
from alive_progress import alive_bar
origin = Poscar.from_file('POSCAR.origin')
run = Vasprun('vasprun.xml')
structure = run.final_structure
trans = SymmetryCloneTransformation(origin.structure, ['Na'])
new = trans.apply_transformation(structure)

new_no_Na = new.copy().remove_species(['Na'])
new.remove_species(['C'])

pairs = []
for site in new:
    if list(site.frac_coords) == [0, 0, 0]:
        first_site = site
        break

for site in new:
    if site != first_site and first_site.distance(site) <= 5:
        pairs.append((first_site, site))

matcher = StructureMatcher(attempt_supercell=True, scale=False)
def is_equiv(pair1, pair2):
    beg1, end1 = pair1
    beg2, end2 = pair2
    tmp1 = new_no_Na.copy()
    tmp2 = new_no_Na.copy()
    for site in pair1:
        tmp1.append(site.species, site.coords, properties=site.properties)
    for site in pair2:
        tmp2.append(site.species, site.coords, properties=site.properties)
    return matcher.fit(tmp1, tmp2)

uniq_pairs = []

with alive_bar(len(pairs)) as progress_bar:
    for pair in pairs:
        pair_unique = True
        progress_bar()
        if len(uniq_pairs) > 0:
            with Pool(8) as pool:
                equivs = pool.starmap(is_equiv, [(pair, uniq) for uniq in uniq_pairs])
                if True in equivs:
                    pair_unique = False
        if pair_unique:
            uniq_pairs.append(pair)

final = new_no_Na.copy()
final.append(first_site.species, first_site.coords, properties=first_site.properties)
for site in [x[1] for x in uniq_pairs]:
    final.append(site.species, site.coords, properties=site.properties)

final.to_file('test.cif')

