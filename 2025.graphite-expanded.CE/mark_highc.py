#!/usr/bin/env python
from pathlib import Path

max_c = 0.19 # 0.33 will still yield large sublattice deviations

for d in Path().iterdir():
    if d.is_dir() and (d / 'str.out').is_file():
        with open(d / 'str.out', 'r', encoding='utf-8') as f:
            n_Na = 0
            n_Vac = 0
            for line in f:
                if 'Vac' in line:
                    n_Vac += 1
                elif 'Na' in line:
                    n_Na += 1
            concentration = n_Na / (n_Na + n_Vac)
            if concentration > max_c and not (d / 'error').is_file():
                print(f'{d}: {concentration} marking with error')
                (d / 'error').touch()
                (d / 'marked_error').touch()
