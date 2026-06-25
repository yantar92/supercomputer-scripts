#!/usr/bin/env python
import sys
from pathlib import Path
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.io.vasp.inputs import Poscar
import pandas as pd
from termcolor import colored


atat_fit_data = pd.read_csv(
    'fit.out',
    sep=' ',
    header=None,
    names=['Concentration', 'Energy',
            'Fitted energy', 'Energy delta',
            'Weight', 'ID'])

opt_dir = Path('optB88')
if not opt_dir.is_dir():
    print(colored(f'{str(opt_dir)} dir does not exist', color='red'))
    sys.exit(1)

relax_data = []

ref_0_run = Vasprun(f'{str(opt_dir)}/0.{str(opt_dir)}.SCF/vasprun.xml')
ref_1_run = Vasprun(f'{str(opt_dir)}/1.{str(opt_dir)}.SCF/vasprun.xml')
energy_0 = ref_0_run.final_energy
energy_1 = ref_1_run.final_energy
print(f'Ref 0 energy: {energy_0}')
print(f'Ref 1 energy: {energy_1}')

ref_poscar = Poscar.from_file('POSCAR')
ref_C = len([site for site in ref_poscar.structure if site.specie.name == 'C'])

for d in opt_dir.iterdir():
    if 'SCF' in d.name and d.is_dir():
        try:
            run = Vasprun(d / 'vasprun.xml')
        except Exception:
            print(colored(f'Failed to read {d.name}/vasprun.xml. Skipping', color='yellow'))
            continue
        if not run.converged:
            print(colored(f'Unconverged run in {d.name}. Skipping', color='yellow'))
            continue
        structure_id = int(d.name.split(sep='.')[0])
        concentration = atat_fit_data.loc[
            atat_fit_data['ID'] == structure_id].iloc[0]['Concentration']
        if concentration is None:
            print(colored('Failed to find structure in fit.out', color='red'))
            sys.exit(1)
        n_C = len([site for site in run.final_structure if site.specie.name == 'C'])
        print(f"{d.name}: {n_C} carbons vs. {ref_C} reference")
        energy = run.final_energy/n_C*ref_C - concentration*energy_1 - (1-concentration)*energy_0
        print(f"{d.name}: {concentration} {energy}")
        relax_data.append({
            'Concentration': concentration,
            'Relax energy, eV': float(energy)
        })
relax_df = pd.DataFrame(relax_data)
relax_df.to_csv('optB88-data.out', sep=' ', index=False)
print(colored('Wrote data to optB88-data.out', color='green'))
