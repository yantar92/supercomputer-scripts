from ase.build import nanotube
from ase import Atom
from ase.visualize import view
import numpy as np
from airsspy import SeedAtoms
from airsspy.seed import BuildcellParam
vacuum = 15
cnt = nanotube(15, 0, length=1, vacuum=vacuum)
seed = SeedAtoms(cnt)
seed += Atom('Na')
radius = (cnt.cell[1, 1] - 2 * vacuum)/2
# seed[-1].posamp = radius
seed.gentags.cylinder = radius

# Can also access per `atom` tags/ketwords just like in ASE
# for i in range(len(seed)):
#     atom = seed[i]
#     # atom.tagname = 'CX'
#     if atom.symbol == 'Na':
#         atom.posamp = 2

seed.write_seed('nanotube.cell')
