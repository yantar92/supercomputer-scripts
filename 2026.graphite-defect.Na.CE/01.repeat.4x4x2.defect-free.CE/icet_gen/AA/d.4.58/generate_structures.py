from pathlib import Path
import numpy as np
import pymatgen.core as pmg
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.io.ase import AseAtomsAdaptor
import ase
from icet import ClusterSpace
from icet.tools.structure_generation import occupy_structure_randomly
from icet.tools.training_set_generation import structure_selection_annealing
from IMDgroup.pymatgen.io.vasp.sets import IMDDerivedInputSet
from IMDgroup.pymatgen.io.vasp.inputs import Incar
from IMDgroup.pymatgen.core.structure import IMDStructure as Structure
from pymatgen.io.vasp.inputs import Poscar, Kpoints
from alive_progress import alive_it

Me = 'Na'
max_c = 0.45  # to reach NaC6 at least
# max_c = 1  # to give some more data for fitting
# exact_Na = None
exact_Na = 12

# Convenience function for supercell size generation
def get_random_supercell_size(max_repeat, max_atoms, n_atoms_in_prim):
    while True:
        nx, ny, nz = np.random.randint(1, max_repeat + 1, size=3)
        if nx * ny * nz * n_atoms_in_prim < max_atoms:
            break
    return nx, ny, nz


input_dir = "."
root="."
# Li+graphite AA
primitive_structure = Poscar.from_file('POSCAR').structure
primitive_structure = AseAtomsAdaptor.get_atoms(primitive_structure)
subelements = [['C'] if a.symbol == 'C' else [Me, 'X']
               for a in primitive_structure]
# Making initial cutoffs large, so that we generate enough data to get reasonable fit
# cutoffs = [10.0, 8.0, 6.0]  # FIXME: may need adjustments
cutoffs = [8.0, 4.0]  # FIXME: may need adjustments
cluster_space = ClusterSpace(primitive_structure, cutoffs, subelements, symprec=1e-3)
print(f"Cluster space size: {len(cluster_space)}")

# We want to add 2 times the number of parameters structures and we
# want the annealing to run for 1e4 steps.
# If we do less then cluster space, the fit is simply impossible
# On the other hand, if cluster space demands something like 10k structures,
# it is impossible to calculate. Maybe that implies that we need smaller cutoffs.
# We do fix cutoffs here, ATAT should be smarter and try other cutoffs, so
# do increments of 200 structures; no more.
# n_structures_to_add = min(len(cluster_space), 200)
n_structures_to_add = 10

# Create a random structure pool
n_random_structures = 10 * n_structures_to_add
max_repeat = 1
max_atoms = 100

graphite_pmg = AseAtomsAdaptor.get_structure(primitive_structure).copy().remove_species([Me])
structures = []
for _ in alive_it(range(n_random_structures), title='Generating random structures'):
    # Create random supercell.
    # supercell = get_random_supercell_size(
    #     max_repeat, max_atoms, len(primitive_structure))
    # structure = primitive_structure.repeat(supercell)
    structure = primitive_structure.copy()
    # Randomize concentrations in the supercell
    n_atoms = len([a for a in structure if a.symbol == Me])

    if exact_Na is None:
        n_Li = np.random.randint(0, int(n_atoms * max_c))
    else:
        n_Li = exact_Na
    n_vac = n_atoms - n_Li

    subs = cluster_space.get_sublattices(primitive_structure)

    concentrations = {}
    for sl in subs:
        if Me in sl.chemical_symbols:
            concentrations[sl.symbol] =\
                {Me: n_Li / n_atoms, 'X': n_vac / n_atoms}
        else:
            concentrations[sl.symbol] = {'C': 1.0}

    # Occupy the structure randomly and store it.
    occupy_structure_randomly(structure, cluster_space, concentrations)
    structures.append(structure)

# We take the first 5 randomly generated structures above and assume they
# were the base structures that we already have done calculations for.
base_structures = structures[0:5]

# Read existing structures, if any
# for d in Path(root).iterdir():
#    if d.is_dir() and d.name.isdigit() and (d / "str.out").is_file():
#        base_structures.append(AseAtomsAdaptor.get_atoms(Structure.from_file(d / 'str.out')))

print(f"Going to add {n_structures_to_add}")
# n_steps = 20000
n_steps = 5000

# start the annealing procedure to minimize the condition number of
# the fit matrix, the base_structures are always included.
other_structures = structures[5:]
indices, traj = structure_selection_annealing(
    cluster_space, other_structures, n_structures_to_add,
    n_steps, base_structures=base_structures)
condition_number_base_structures = traj[-1]

# collect the extra structures
training_structures_extra = [other_structures[ind] for ind in indices]
print(f'Produced {len(training_structures_extra)} structures; retaining {n_structures_to_add}')
all_structures = base_structures + training_structures_extra
all_structures = all_structures[:n_structures_to_add]
all_structures2 = [AseAtomsAdaptor.get_structure(s) for s in all_structures]
# for s in all_structures2:
#     s.remove_species(['X'])
    # AA should not need extra constraints
    # s.add_site_property(
    #     "selective_dynamics",
    #     # a axis is across the layers. We constrain motion along the layers to avoid AB-AA stacking drift
    #     [[True, True, True] if site.specie == pmg.Element(Me) else [True, False, False]
    #      for site in s])

# FIXME: random structures may contain duplicates
from IMDgroup.pymatgen.core.structure import structure_matches
uniq_structs = []
uniq_structs_idx = []
for idx, s in alive_it(list(enumerate(all_structures2)), title="Filtering out duplicates"):
    # if not structure_matches(s, uniq_structs, multithread=False) and\
    #    not structure_matches(s, known_structures, multithread=False):
    #     uniq_structs.append(s)
    s2 = s.copy()
    s2.remove_species(['X'])
    if not structure_matches(s2, uniq_structs, multithread=True):
        uniq_structs.append(s2)
        uniq_structs_idx.append(idx)

Path(root).mkdir(exist_ok=True)
# inputset = IMDDerivedInputSet(
#     directory=input_dir,
#     # user_incar_settings={
#     #     'ISIF': Incar.ISIF_FIX_NONE,
#     #     'EDIFFG': -0.03,
#     #     'NCORE': 16,
#     #     'IBRION': Incar.IBRION_IONIC_RELAX_CGA},
#     # # Simplify things
#     # user_kpoints_settings={'grid_density': 10000}
# )
# for idx, s in enumerate(uniq_structs):
#     inputset.structure = s
#     inputset.write_input(f"{root}/{idx:02d}")
for idx in uniq_structs_idx:
    s = all_structures2[idx]
    s.__class__ = Structure
    # Offset by 100 to not interfere with existing ATAT folders
    dir_idx = idx + 100
    p = Path(f"{root}/{dir_idx:d}")
    while p.is_dir():
        dir_idx += 1
        p = Path(f"{root}/{dir_idx:d}")
    p.mkdir()
    s.to_file(p / "str.out")
