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


def _read_dir(li_entry, path: Path):
    """Read DIR and return pandas frame with voltage against LI_ENTRY.
    """
    vasp_dirs = []
    entries = []
    for p in path.iterdir():
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
    plotter = VoltageProfilePlotter(xaxis='x_form')
    x, voltage = plotter.get_plot_data(electrode, term_zero=False)
    voltage_data = {'x': x, 'voltage': voltage}

    # Create DataFrame and sort by ion concentration
    df = pd.DataFrame(voltage_data).sort_values("x")
    base_formula = str(electrode.fully_charged_entry.composition)
    base_formula = re.sub(
        r'([A-Z][a-z]*)(\d+)',
        lambda m: f'{m.group(1)}', base_formula)
    df.base_formula = base_formula
    # Save and plot results
    df.to_csv(path / 'voltage.out', sep=' ', index=False)
    print(f"Voltage profile saved to {path}/voltage.out")
    return df


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
    all_dirs = [Path('.')] + [Path(p) for p in args.extra_data]
    all_voltages = [_read_dir(li_entry, d) for d in all_dirs]

    plt.figure(figsize=(10, 6))
    for df in all_voltages:
        plt.step(df['x'], df['voltage'], where='post')
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.7)
    plt.xlabel(f'Concentration (x in {args.ion.symbol}$_{{x}}${all_voltages[0].base_formula})')
    plt.ylabel(f'Voltage vs. {args.ion.symbol}/{args.ion.symbol}⁺ (V)')
    plt.title('Voltage Profile')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig('voltage.png', dpi=300)
    plt.close()
    print(f"Voltage graphs saved to voltage.png")

if __name__ == "__main__":
    main()
