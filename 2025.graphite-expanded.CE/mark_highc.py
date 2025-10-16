#!/usr/bin/env python
from pathlib import Path

max_c = 0.34 # 0.33 will still yield large sublattice deviations
max_c = 0.67 # 0.25 in PhaseDiagram convention: LiC3 = Li0.67C2. For manual convex hull
counter = 0
def process_dir(d):
    if d.is_dir() and (d / 'str.out').is_file():
        with open(d / 'str.out', 'r', encoding='utf-8') as f:
            n_Na = 0
            n_Vac = 0
            for line in f:
                if 'Vac' in line:
                    n_Vac += 1
                elif 'Na' in line or 'Li' in line:
                    n_Na += 1
            concentration = n_Na / (n_Na + n_Vac) if n_Na + n_Vac > 0 else None
            if concentration is not None and concentration > max_c and not (d / 'error').is_file():
                global counter
                counter += 1
                print(f'{d}: {concentration} marking with error')
                (d / 'error').touch()
                (d / 'error_highc').touch()
extra_dirs = [Path()]
for d in Path().iterdir():
    if d.is_dir() and not (d / 'str.out').is_file():
        extra_dirs.append(d)
print(extra_dirs)
for root in extra_dirs:
    for d in root.iterdir():
        process_dir(d)
print(f"Total number of concentrations above {max_c} is {counter}")
