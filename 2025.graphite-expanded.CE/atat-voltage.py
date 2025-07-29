#!/usr/bin/env python
"""Plot voltage profile from ATAT results using pymatgen's battery analysis tools.
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
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.apps.battery.insertion_battery import InsertionElectrode
import pandas as pd
import matplotlib.pyplot as plt
from alive_progress import alive_it


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "metal_vasprun",
        help="Path to reference VASP SCF calculation for pure ion structure.")
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
            # Store volume in entry data for voltage calculation
            entry = ComputedEntry(comp, vaspdir.final_energy)
            entry.data["volume"] = vaspdir.structure.volume
            entries.append(entry)
        except Exception as e:
            print(f"Skipping {target_dir}: {str(e)}")

    # Create insertion electrode
    electrode = InsertionElectrode.from_entries(
        entries,
        working_ion_entry=li_entry,
        strip_structures=False  # We need volume data
    )

    # Extract voltage profile data
    voltage_data = []
    for pair in electrode.voltage_pairs:
        # Calculate Ion concentration (x in Ion_x Host)
        x_charge = pair.x_charge
        x_discharge = pair.x_discharge

        voltage_data.append({
            "x": x_charge,
            "voltage": pair.voltage
        })
        voltage_data.append({
            "x": x_discharge,
            "voltage": pair.voltage
        })

    # Create DataFrame and sort by ion concentration
    df = pd.DataFrame(voltage_data).sort_values("x")

    # Save and plot results
    df.to_csv('voltage.out', sep=' ', index=False)

    plt.figure(figsize=(10, 6))
    plt.xlim((0, 1))
    plt.step(df['x'], df['voltage'], where='post', color='blue', linewidth=2)
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
    plt.xlabel(f'Concentration (x in {args.ion.symbol}$_{{x}}$Host)')
    plt.ylabel(f'Voltage vs. {args.ion.symbol}/{args.ion.symbol}⁺ (V)')
    plt.title('Voltage Profile')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('voltage.png', dpi=300)
    plt.close()

    print("Voltage profile saved to voltage.png and voltage.out")

if __name__ == "__main__":
    main()
