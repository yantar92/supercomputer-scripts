from IMDgroup.pymatgen.cli.imdg_analyze import read_vaspruns
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.analysis.ewald import EwaldSummation
import pymatgen.core as pmg
import matplotlib.pyplot as plt
import os
from pathlib import Path
from matplotlib.markers import MarkerStyle
import numpy as np

def includep(p):
    if not os.path.isfile(os.path.join(p, "error")) and "gorun" not in p:
        return True
    return False

def get_energies(runs, ref_Na, ref_Li, ref_C):
    energies = []
    ewald_energies = []
    concentrations = []
    element_valences = {"Na": 1, "Li": 1, "C": 0}
    for run in runs:
        if not run.data['converged']:
            continue
        s = run.structure
        s.unset_charge()
        s.add_oxidation_state_by_element(element_valences)
        n_Li, n_Na, n_C = 0, 0, 0
        for site in s:
            if site.specie.name == 'Li':
                n_Li += 1
            if site.specie.name == 'Na':
                n_Na += 1
            if site.specie.name == 'C':
                n_C += 1
        fen = run.energy - n_Li * ref_Li - n_Na * ref_Na - n_C * ref_C
        energies.append(fen/len(s))
        concentrations.append((n_Li+n_Na)/n_C)
        # energies.append(run.energy)
        ewald = EwaldSummation(s)
        ewald_energies.append(ewald.total_energy/len(s))
    uniq_c = []
    uniq_en = []
    uniq_ew = []
    for c, en, ewald in zip(concentrations, energies, ewald_energies):
        if not np.isclose(uniq_c, c, atol=0.01).any():
            uniq_c.append(c)
            uniq_en.append(en)
            uniq_ew.append(ewald)
        else:
            for idx, c0 in enumerate(uniq_c):
                if np.isclose(c, c0, atol=0.01) and en < uniq_en[idx]:
                    uniq_en[idx] = en
                    uniq_ew[idx] = ewald
    return uniq_c, uniq_en, uniq_ew
    # return concentrations, energies, ewald_energies


# prefix = "./data"
prefix = Path(".")
# prefix = Path("/users/radchenk/data")
# prefix = "/home/yantar92/lumi"

run_ref_Na = Vasprun(f'{prefix}/2025.graphite-exanded.Na.CE/00.reference/Na.mp-127.cubic.229.KPOINTS.2500.0.SCF/vasprun.xml')
ref_Na = run_ref_Na.final_energy / len(run_ref_Na.final_structure)
run_ref_Li = Vasprun(f'{prefix}/2025.graphite.Li.CE/00.reference/Li.mp-135.cubic.229.KPOINTS.5000.0.SCF/vasprun.xml')
ref_Li = run_ref_Li.final_energy / len(run_ref_Li.final_structure)

data = {}

plt.figure(figsize=(8,6))

all_markers = list(MarkerStyle.markers.keys())
idx = 0

cmap = plt.get_cmap('RdBu', 10)

# , "2025.graphite-exanded.Na.CE/02.CE.fast"
# "2025.graphite.Li.CE/03.CE.fast"
for top_path in ["2025.graphite.Li.CE/03.CE.fast"]:
    elem_label = "Li" if "Li" in top_path else "Na"
    top_path = Path(top_path)
    # , "AA.dilute", "AB.dilute", "AB", "AA.dilute"
    for stacking in ["AA"]:
        stacking_label = "AA" if "AA" in stacking else "AB"
        stacking = Path(stacking)
        # , "strain.c.0.30"
        for strain in ["strain.c.0.00"]:
            strain_label = "0%" if "0.00" in strain else "30%"
            strain = Path(strain)
            path = prefix / top_path / stacking / strain
            run_ref_C = Vasprun(path / "0" / "vasprun.xml")
            ref_C = run_ref_C.final_energy / len(run_ref_C.final_structure)
            runs = read_vaspruns(path, path_filter=includep)
            concentrations, energies, ewald_energies =\
                get_energies(runs, ref_Na, ref_Li, ref_C)
            data[top_path, stacking, strain] = {
                'concentrations': concentrations,
                'energies': energies,
                'ewald_energies': ewald_energies
                }
            plt.scatter(
                energies, ewald_energies,
                c=concentrations, cmap=cmap,
                label=f"{elem_label}, {stacking_label}, {strain_label}",
                marker=all_markers[idx % len(all_markers)]
                )
            idx += 1
            
plt.xlabel('Formation energy, eV/atom')
plt.ylabel('Ewald energy, eV/atom')
plt.legend()
plt.colorbar(label="Concentration")
# plt.show()

plt.savefig('ewald_vs_formation_energy_hull.png')
