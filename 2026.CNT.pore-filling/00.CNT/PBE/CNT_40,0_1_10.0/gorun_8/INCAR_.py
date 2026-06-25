
import numpy as np
from ase.eos import EquationOfState
from ase.io import read


SCAN_THRESHOLD = 0.04 # scan threshold

# 1. Create your configurations (looping over z-lengths)
# Assume 'atoms' is your starting structure
z_original = atoms.cell[2, 2]
z_factors = np.linspace(1 - SCAN_THRESHOLD, 1 + SCAN_THRESHOLD, 7) # 7 points is usually enough
energies = []
volumes = []

for f in z_factors:
    atoms.cell[2, 2] = z_original * f
    # Important: scale_atoms=True moves atoms proportionally in z
    atoms.set_cell(atoms.cell, scale_atoms=True)
    energies.append(atoms.get_potential_energy())
    volumes.append(atoms.get_volume())

# 2. Fit the data
# Even though we varied Z, we fit Energy vs. Volume
eos = EquationOfState(volumes, energies)
v0, e0, B = eos.fit()

# 3. Calculate your optimal Z from the optimal Volume
opt_z = v0 / (atoms.cell[0,0] * atoms.cell[1,1] * np.sin(np.deg2rad(atoms.cell.cellpar()[5])))

atoms.cell[2, 2] = opt_z
# Important: scale_atoms=True moves atoms proportionally in z
atoms.set_cell(atoms.cell, scale_atoms=True)
energies.append(atoms.get_potential_energy())
print(f"Optimal z-length: {opt_z}, E = {energies[-1]}")
for f, energy in zip(z_factors, energies):
    print(f"{z_original * f} {energy}")
print(f"{opt_z} {energies[-1]}")
