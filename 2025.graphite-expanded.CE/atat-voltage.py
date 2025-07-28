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
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from alive_progress import alive_it


def _get_normalized_energy(index_dir, ion, base_N):
    """Compute normalized energy for INDEX_DIR.
    BASE_N is the number of atoms in base structure.
    """
    vaspdir = IMDGVaspDir(index_dir / "ATAT.SCF")
    if vaspdir.final_energy is None:
        vaspdir = IMDGVaspDir(index_dir)
    N_ion = len([s for s in vaspdir.initial_structure if s.specie == ion])
    N_nonion = len(vaspdir.initial_structure) - N_ion
    if vaspdir.final_energy is None:
        return float('inf')
    return vaspdir.final_energy / N_nonion * base_N


def _get_true_gs(gs_data, fit_data, extra_paths, ion, base_N):
    """Check if any point from FIT_DATA is below hull."""
    if extra_paths is None:
        extra_paths = []
    concentrations = []
    energies = []
    for _, row in alive_it(fit_data.iterrows(), total=len(fit_data), title="Reading VASP outputs"):
        c, index = row['concentration'], int(row['index'])
        energy = min([
            _get_normalized_energy(Path(d) / str(index), ion, base_N)
            for d in ['./'] + extra_paths if (Path(d) / str(index)).is_dir()
        ])
        concentrations.append(c)
        energies.append(energy)
    # Create DataFrame and find min energy per concentration
    df = pd.DataFrame({'concentration': concentrations, 'energy': energies})
    min_df = df.groupby('concentration', as_index=False)['energy'].min()
    min_df = min_df.sort_values('concentration')
    # Build ground state line (lowest-energy phase diagram)
    gs_concentrations = []
    gs_energies = []
    for _, row in min_df.iterrows():
        c, energy = row['concentration'], row['energy']
        # While there are at least 2 points, check if current point makes
        # the previous point non-ground-state
        while len(gs_concentrations) >= 2:
            c0, e0 = gs_concentrations[-2], gs_energies[-2]  # Previous hull point
            c1, e1 = gs_concentrations[-1], gs_energies[-1]  # Last hull point
            # Calculate expected energy at c if it were on the line between c0 and c1
            slope = (e1 - e0) / (c1 - c0)
            expected_energy = e0 + slope * (c - c0)
            # If current energy is below the line, remove non-ground-state point
            if energy < expected_energy:
                gs_concentrations.pop()
                gs_energies.pop()
            else:
                break
        gs_concentrations.append(c)
        gs_energies.append(energy)
    # Final check: ensure last segment doesn't violate convexity
    while len(gs_concentrations) >= 3:
        c0, e0 = gs_concentrations[-3], gs_energies[-3]
        c1, e1 = gs_concentrations[-2], gs_energies[-2]
        c2, e2 = gs_concentrations[-1], gs_energies[-1]
        slope1 = (e1 - e0) / (c1 - c0)
        expected = e0 + slope1 * (c2 - c0)
        if e2 < expected:
            gs_concentrations.pop(-2)
            gs_energies.pop(-2)
        else:
            break
    # Compare with ATAT hull
    for c, energy in zip(gs_concentrations, gs_energies):
        mask = np.isclose(gs_data['concentration'], c)
        if not mask.any():
            continue
        atat_energy = gs_data.loc[mask, 'energy'].min()
        if energy < atat_energy:
            print(f"Found energy below ATAT hull!: c={c}, energy={energy} (< {atat_energy})")
    return gs_concentrations, gs_energies

def main():
    """DITTO.
    """

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
        "It is a list of paths mirroring ATAT folder structure. "
        "the paths will be searched for structured from fit.out and "
        "their energy will be considered when checkign the convex hull.",
        type=str,
        nargs="+"
    )

    args = parser.parse_args()

    ion_run = IMDGVaspDir(Path(args.metal_vasprun))['vasprun.xml']
    assert ion_run is not None
    assert ion_run.converged
    assert all(s.specie == args.ion for s in ion_run.final_structure)
    en_ion = ion_run.final_energy / len(ion_run.final_structure)

    max_c_run = IMDGVaspDir(Path("1/ATAT.SCF"))['vasprun.xml']
    if max_c_run is None:
        max_c_run = IMDGVaspDir(Path("1"))['vasprun.xml']
    assert max_c_run is not None
    reverse_concentration = False
    max_N_ion = len([s for s in max_c_run.final_structure
                     if s.specie == args.ion])
    if max_N_ion == 0:
        # reverse concentration range Ion..Vac, not Vac..Ion
        reverse_concentration = True
        max_c_run = IMDGVaspDir(Path("0/ATAT.SCF"))['vasprun.xml']
        if max_c_run is None:
            max_c_run = IMDGVaspDir(Path("0"))['vasprun.xml']
        assert max_c_run is not None
        max_N_ion = len([s for s in max_c_run.final_structure
                         if s.specie == args.ion])
    assert max_N_ion > 0
    base_N = len(max_c_run.final_structure) - max_N_ion
    print(f"ion:{max_N_ion}; matrix:{base_N}")

    gs_data = pd.read_csv(
        'gs.out', sep=' ', header=None,
        names=['concentration', 'energy', 'fitted_energy', 'index'])
    fit_data = pd.read_csv(
        'fit.out', sep=' ', header=None,
        names=['concentration', 'energy',
               'fitted energy', 'energy delta',
               'weight', 'index']
    )
    prev_c = None
    prev_en = None
    voltage = []
    concentrations = []
    true_gs = _get_true_gs(gs_data, fit_data, args.extra_data, args.ion, base_N)
    for cur_en, energy in reversed(true_gs) if reverse_concentration else true_gs:
        if reverse_concentration:
            c = 1 - c
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
