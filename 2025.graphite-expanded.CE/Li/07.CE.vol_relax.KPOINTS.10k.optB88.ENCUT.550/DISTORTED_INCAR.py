import os
from pathlib import Path
from ase.constraints import FixAtoms
from ase.filters import FrechetCellFilter
from ase.optimize import BFGS
from ase.io import write as ase_write

fix_c = FixAtoms(mask=[atom.symbol == "C" for atom in atoms])
atoms.set_constraint(fix_c)
# Do not use VASP relaxation. We roll out own and just use VASP for
# SCF energy calculations.  Keep wavecar around for speedup.
atoms.calc.set(nsw=0,istart=1,lwave=True)

# ExpCellFilter mask (Voigt: xx, yy, zz, yz, xz, xy):
# We only relax xx, yy, and zz; not shear (stacking change)
cell_filter = FrechetCellFilter(
    atoms,
    mask=[True, True, True, False, False, False]
)

optimizer = BFGS(cell_filter, trajectory="opt.traj", logfile="opt.log")

optimizer.run(fmax=0.005) # 0.02 gives stress components above 1kB in some cases
ase_write('CONTCAR', atoms, format="vasp")
if Path('WAVECAR').is_file():
    Path('WAVECAR').unlink()
print("Done. Relaxed structure written to CONTCAR")
