from airsspy import SeedAtoms, Buildcell
from ase import Atoms
from ase.build import nanotube

vacuum = 15
tube = nanotube(15, 0, length=1, vacuum=vacuum)

tube.extend(Atoms('Na'))
seed = SeedAtoms(tube)

seed.gentags.supercell = '1 1 1'
seed.gentags.slack = 0.1
seed.gentags.minsep = [5.0, {'C-C': 1, 'Na-Na': 3.59346, 'C-Na': 2}]
seed.gentags.fix = True
# seed.gentags.cylinder = radius = (tube.cell[1, 1] - 2 * vacuum)/2
radius = (tube.cell[1, 1] - 2 * vacuum)/2
for atom in seed:
    if atom.symbol == 'C':
        atom.fix = True
        atom.posamp = 0
    else:
        atom.zamp = -1
        atom.xamp = radius
        atom.yamp = radius
        atom.adatom = True
        atom.num = 12
        atom.position = [seed.cell[0, 0]/2, seed.cell[1, 1]/ 2, 0]
print('\n'.join(seed.get_cell_inp_lines()))
bc = Buildcell(seed)
for idx in range(20):
    atoms = bc.generate(timeout=100)
    atoms.write(f'{idx}.cif')

