#!/usr/bin/env python
"""Collect all structure IDs near hull.
"""
import argparse
from pathlib import Path
import numpy as np
from pymatgen.core import Element
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
from alive_progress import alive_it


def get_entries_recursively(
        path: Path,
        extra_data: list[Path] | None = None,
        extra_data_threshold: float = 0.0001) -> list:
    """Scan PATH for energies and return a list of computed entries.
    EXTRA_DATA is a list of relative directories to be scanned in addition to
    PATH.
    """
    # Collect all computed entries
    entries = []
    if extra_data is None:
        extra_data = []
    path = Path(path)
    extra_dirs = [Path(path) / Path(p) for p in extra_data]

    vasp_dirs = []
    extra_vasp_dirs = []
    for parent in [path] + extra_dirs:
        if not parent.is_dir():
            continue
        for p in parent.iterdir():
            if p.is_dir() and p.name.isdigit():
                if parent == path:
                    vasp_dirs.append(p)
                else:
                    extra_vasp_dirs.append(p)

    all_vasp_dirs = vasp_dirs + extra_vasp_dirs
    n_rejected_perturbs = 0
    n_skipped = 0
    for p in alive_it(all_vasp_dirs, total=len(all_vasp_dirs), title='Reading VASP outputs'):
        # Check for ATAT.SCF directory
        scf_dir = p / "ATAT.SCF"
        target_dir = scf_dir if scf_dir.is_dir() else p
        try:
            vaspdir = IMDGVaspDir(target_dir)
            if vaspdir.final_energy is None:
                continue
            if not vaspdir.converged:
                if (target_dir / "INCAR").is_file():
                    print(f"Skipping {target_dir}: unconverged")
                    n_skipped += 1
                else:
                    pass
                    n_skipped += 1
                    # print(f"Skipping {target_dir}: missing VASP inputs")
                continue
            # vaspdir_relax = IMDGVaspDir(p / "ATAT")
            comp = vaspdir.structure.composition
            entry = ComputedEntry(comp, vaspdir.final_energy)
            # Store volume in entry data
            entry.data["volume"] = vaspdir.structure.volume
            entry.data["ID"] = p
            entry.data["is_extra"] = p not in vasp_dirs
            # vol2 = vaspdir_relax.structure.volume
            # vol1 = vaspdir_relax.initial_structure.volume
            # entry.data["vol%"] = (vol2 - vol1) / vol1 * 100
            is_duplicate = False
            for e in entries:
                if not entry.data.get('is_extra', False):
                    continue
                if np.isclose(
                        e.energy_per_atom, entry.energy_per_atom,
                        extra_data_threshold)\
                   and e.composition == entry.composition:
                    is_duplicate = True
                    break
            if not is_duplicate:
                entries.append(entry)
            else:
                n_rejected_perturbs += 1
        except Exception as e:
            print(f"Skipping {target_dir}: {str(e)}")
            n_skipped += 1
    print(f"Read {len(vasp_dirs)} runs and {len(extra_vasp_dirs)} extra runs")
    print(f"Skipped: {n_skipped}; Extra runs close to main:"
          f" {n_rejected_perturbs}/{len(extra_vasp_dirs)}")
    return entries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "metal_vasprun",
        help="Path to reference VASP SCF calculation for pure ion structure.")
    parser.add_argument(
        "matrix_vasprun",
        help="Path to reference VASP SCF calculation for pure matrix structure (default: 0/ATAT.SCF).")
    parser.add_argument(
        "--ion", default="Li",
        help="Working ion element (default: Li)",
        type=Element)
    parser.add_argument(
        "--show_unstable", default=0.050,
        help="Show unstable entries with energy above hull less than this value (eV/atom) (default: 0.050)",
        type=float)
    parser.add_argument(
        "--extra_data",
        help="Extra data to consider. "
        "List of paths mirroring ATAT folder structure. "
        "Paths will be searched for structures from fit.out.",
        type=str,
        nargs="*",
        default=[]
    )
    parser.add_argument(
        "--extra_data_threshold", default=0.001,
        help="Min difference with main data to omit plotting extra data (default: 0.001eV/atom)",
        type=float)
    args = parser.parse_args()

    # Read pure Li reference energy
    li_run = IMDGVaspDir(Path(args.metal_vasprun))
    li_energy = li_run.final_energy
    li_entry = ComputedEntry(li_run.structure.composition, li_energy)
    li_entry.data["ID"] = Path(args.metal_vasprun)
    print(f"{args.ion} energy: {li_entry.energy_per_atom}")

    # Read pure matrix reference energy
    c_run = IMDGVaspDir(Path(args.matrix_vasprun))
    c_energy = c_run.final_energy
    c_entry = ComputedEntry(c_run.structure.composition, c_energy)
    c_entry.data["volume"] = c_run.structure.volume
    c_entry.data["ID"] = Path(args.matrix_vasprun)
    # vol2 = c_run.structure.volume
    # vol1 = c_run.initial_structure.volume
    # c_entry.data["vol%"] = (vol2 - vol1) / vol1 * 100
    print(f"C energy: {c_entry.energy_per_atom}")

    path = Path('.')
    print(f"Extra paths: {args.extra_data}")
    entries = get_entries_recursively(
        Path(path), args.extra_data, args.extra_data_threshold)
    phd = PhaseDiagram(entries=entries + [li_entry, c_entry],
                       elements=[Element("C"), args.ion])
    plotter = PDPlotter(phd, show_unstable=args.show_unstable)
    _, stable_entries, unstable_entries = plotter.pd_plot_data
    data = [{
        'ID': str(entry.data.get("ID")),
        'Energy': entry.energy_per_atom,
        'Concentration': coords[0],
        'Formation Energy (meV/atom)': coords[1] * 1000
    } for entry, coords in unstable_entries.items()
            if phd.get_e_above_hull(entry) is not None
            and phd.get_e_above_hull(entry) < args.show_unstable]
    stable_data = [{
        'ID': str(entry.data.get("ID")),
        'Energy': entry.energy_per_atom,
        'Concentration': coords[0],
        'Formation Energy (meV/atom)': coords[1] * 1000
    } for coords, entry in stable_entries.items()]
    data.extend(stable_data)
    for rec in data:
        print(rec['ID'])


if __name__ == "__main__":
    main()
