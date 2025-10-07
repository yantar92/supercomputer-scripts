#!/usr/bin/env python
"""Plot formation energy hull profile from ATAT results.
The script should run from ATAT folder containing ATAT calculation subfolders.
The script accepts two mandatory parameters: working battery ion atom
(default: Li) and reference SCF vasprun containing the ion base
structure (e.g. BCC Li).
INCAR parameters and KPOINTS should match for ATAT runs and the base
structure.
Saves formation vs. concentration plot into "formation_en.png".
"""
import argparse
import re
from pathlib import Path
from pymatgen.core import Element
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.apps.battery.insertion_battery import InsertionElectrode
from pymatgen.apps.battery.plotter import VoltageProfilePlotter
import pandas as pd
import matplotlib.pyplot as plt
from alive_progress import alive_it


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "metal_vasprun",
        help="Path to reference VASP SCF calculation for pure ion structure.")
    parser.add_argument(
        "--matrix_vasprun",
        default='./0/ATAT.SCF/',
        help="Path to reference VASP SCF calculation for pure matrix structure (default: 0/ATAT.SCF).")
    parser.add_argument(
        "--ion", default="Li",
        help="Working ion element (default: Li)",
        type=Element)
    parser.add_argument(
        "--extra_data",
        help="Extra data to consider. "
        "List of paths mirroring ATAT folder structure. "
        "Paths will be searched for structures from fit.out.",
        type=str,
        nargs="*",
        default=[]
    )
    args = parser.parse_args()

    # Read pure Li reference energy
    li_run = IMDGVaspDir(Path(args.metal_vasprun))
    li_energy = li_run.final_energy
    li_entry = ComputedEntry(li_run.structure.composition, li_energy)
    print(f"{args.ion} energy: {li_entry.energy_per_atom}")

    # Read pure matrix reference energy
    c_run = IMDGVaspDir(Path(args.matrix_vasprun))
    c_energy = c_run.final_energy
    c_entry = ComputedEntry(c_run.structure.composition, c_energy)
    c_entry.data["volume"] = c_run.structure.volume
    print(f"C energy: {c_entry.energy_per_atom}")

    # Collect all computed entries
    entries = []
    all_dirs = [Path('.')] + [Path(p) for p in args.extra_data]

    vasp_dirs = []
    for parent in all_dirs:
        if not parent.is_dir():
            continue
        for p in parent.iterdir():
            if p.is_dir() and p.name.isdigit():
                vasp_dirs.append(p)

    for p in alive_it(vasp_dirs, total=len(vasp_dirs), title='Reading VASP outputs'):
        # Check for ATAT.SCF directory
        scf_dir = p / "ATAT.SCF"
        target_dir = scf_dir if scf_dir.is_dir() else p
        try:
            vaspdir = IMDGVaspDir(target_dir)
            if vaspdir.final_energy is None:
                continue
            comp = vaspdir.structure.composition
            entry = ComputedEntry(comp, vaspdir.final_energy)
            # Store volume in entry data
            entry.data["volume"] = vaspdir.structure.volume
            entries.append(entry)
        except Exception as e:
            print(f"Skipping {target_dir}: {str(e)}")

    xs = []
    ens = []
    for entry in entries:
        li_ratio = entry.composition.get_atomic_fraction(args.ion)
        volume_norm = entry.data['volume'] / c_entry.data['volume']
        energy_per_atom = (entry.energy_per_atom - li_ratio * li_entry.energy_per_atom - (1 - li_ratio) * c_entry.energy_per_atom)
        normalized_energy = energy_per_atom * entry.composition.num_atoms / volume_norm
        xs.append(li_ratio)
        ens.append(normalized_energy)

    # Create DataFrame and sort by ion concentration
    df = pd.DataFrame({'x': xs, 'formation energy': ens}).sort_values("x")

    # Save and plot results
    df.to_csv('formation_en.out', sep=' ', index=False)

    plt.figure(figsize=(10, 6))
    plt.scatter(df['x'], df['formation energy'], color='blue', linewidth=2)
    plt.xlabel('Concentration')
    plt.ylabel('Formation energy per reference carbon cell')
    plt.title('Formation energies')
    plt.tight_layout()
    plt.savefig('formation_en.png', dpi=300)
    plt.close()

    print("Formation energy profile saved to formation_en.png and formation_en.out")

if __name__ == "__main__":
    main()
