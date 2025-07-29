#!/usr/bin/env python
"""Plot voltage provide from ATAT results, assuming single atom insertion.
The script should run from ATAT folder containing gs.out file.
The script accepts two mandatory parameters: working battery ion atom
(default: Li) and reference SCF vasprun containing the ion base
structure (e.g. BCC Li).
INCAR parameters and KPOINTS should match for ATAT runs and the base
structure.
Saves voltage vs. concentration plot into "voltage.png".
"""
import argparse
from pathlib import Path
from pymatgen.core import Element
from pymatgen.io.vasp.outputs import Vasprun
import pandas as pd
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "metal_vasprun",
        help="Path to reference VASP SCF calculation for pure ion structure.")
    parser.add_argument(
        "--ion", default="Li",
        help="Working ion element (default: Li)",
        type=lambda x: Element(x))

    args = parser.parse_args()

    ion_run = Vasprun(Path(args.metal_vasprun) / "vasprun.xml")
    assert ion_run.converged
    assert all(s.specie == args.ion for s in ion_run.final_structure)
    en_ion = ion_run.final_energy / len(ion_run.final_structure)

    try:
        max_c_run = Vasprun(Path("1/ATAT.SCF/vasprun.xml"))
    except FileNotFoundError:
        max_c_run = Vasprun(Path("1/vasprun.xml"))
    reverse_concentration = False
    max_N_ion = len([s for s in max_c_run.final_structure
                     if s.specie == args.ion])
    if max_N_ion == 0:
        # reverse concentration range Ion..Vac, not Vac..Ion
        reverse_concentration = True
        try:
            max_c_run = Vasprun(Path("0/ATAT.SCF/vasprun.xml"))
        except FileNotFoundError:
            max_c_run = Vasprun(Path("0/vasprun.xml"))
        max_N_ion = len([s for s in max_c_run.final_structure
                         if s.specie == args.ion])
    assert max_N_ion > 0
    base_N = len(max_c_run.final_structure) - max_N_ion
    print(f"ion:{max_N_ion}; matrix:{base_N}")

    gs_data = pd.read_csv(
        'gs.out', sep=' ', header=None,
        names=['concentration', 'energy', 'fitted_energy', 'index'])
    prev_c = None
    prev_en = None
    voltage = []
    concentrations = []
    for _, row in gs_data.iloc[::-1].iterrows() if reverse_concentration else gs_data.iterrows():
        c, index = row['concentration'], int(row['index'])
        if reverse_concentration:
            c = 1 - c
        try:
            run = Vasprun(Path(str(index)) / "ATAT.SCF" / "vasprun.xml")
        except FileNotFoundError:
            run = Vasprun(Path(str(index)) / "vasprun.xml")
        N_ion = len([s for s in run.final_structure if s.specie == args.ion])
        N_nonion = len(run.final_structure) - N_ion
        # Norm per c=1 cell matrix
        cur_en = run.final_energy / N_nonion * base_N
        if prev_c is not None and prev_en is not None:
            concentrations.append(prev_c)
            voltage.append(
                # take care to norm per e, outputting in V
                -(cur_en - prev_en - en_ion*max_N_ion*(c - prev_c)) / (c - prev_c) / max_N_ion
            )
            print(f"c: {prev_c:.3f} Δc: {(c - prev_c):.3f} ΔE: {(cur_en - prev_en):.3f} - {(en_ion*max_N_ion*(c - prev_c)):.3f} = {(cur_en - prev_en - en_ion*max_N_ion*(c - prev_c)):.3f} V: {voltage[-1]}")
        prev_c, prev_en = c, cur_en

    data = pd.DataFrame({'concentration': concentrations, 'voltage': voltage})
    data.to_csv('voltage.out', sep=' ')

    plt.figure(figsize=(8, 6))
    plt.step(concentrations, voltage, where='post')
    plt.axhline(y=0, color='gray', linestyle='--')
    plt.ylabel('Voltage vs me ion (V)')
    plt.xlabel('Concentration')
    plt.savefig('voltage.png')
    plt.close()


if __name__ == "__main__":
    main()
