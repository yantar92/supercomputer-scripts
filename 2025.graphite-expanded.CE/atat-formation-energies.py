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
import itertools
from pathlib import Path
import numpy as np
import pandas as pd
from pymatgen.core import Element, Composition
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir
from pymatgen.entries.computed_entries import ComputedEntry
from pymatgen.analysis.phase_diagram import PhaseDiagram, PDPlotter
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from alive_progress import alive_it

def _to_subscript(text: str) -> str:
    """
    Convert any trailing (or interior) integer characters in a composition
    string to LaTeX sub‑script form.

    Example
    -------
    >>> _to_subscript("LiC6")
    'LiC$_{6}$'
    >>> _to_subscript("Fe2O3")
    'Fe$_{2}$O$_{3}$'
    """
    # Replace each group of digits with a LaTeX subscript block.
    # ``re.sub`` is safe for strings that contain no digits – it simply returns the original.
    return re.sub(r'(\d+)', r'$_{\1}$', text)


def get_entries_recursively(
        path: Path,
        extra_data: list[Path] | None = None,
        extra_data_threshold: float = 0.001) -> list:
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


DEFAULT_FONT_SIZE = 10

def plot_custom_phase_diagram(
        phd, ax, ion_element, matrix_element,
        max_conc=1.0, show_unstable=1000,
        font_size=DEFAULT_FONT_SIZE, title=None, ymin=None, ymax=None):
    """Custom phase diagram plot that overrides pymatgen's hardcoded font settings."""

    energy_mult = 1000
    
    # Create a PDPlotter to access the plotting data
    plotter = PDPlotter(phd, show_unstable=show_unstable)
    lines, stable_entries, unstable_entries = plotter.pd_plot_data
    all_stable_en = [c[1] for c in stable_entries]
    all_unstable_en = [c[1] for _, c in unstable_entries.items()]
    # print(f"Stable: {len(stable_entries)} ({min(all_stable_en)}..{max(all_stable_en)}eV); Unstable: {len(unstable_entries)} ({min(all_unstable_en)}..{max(all_unstable_en)}eV)")

    # Save all the entries into formation_en.txt file
    data_file = 'formation_en.txt'
    gs_data_file = 'formation_en_gs.txt'
    min_data_file = 'formation_en_min.txt'
    data = [{
        'ID': str(entry.data.get("ID")),
        'Energy': entry.energy_per_atom,
        'Concentration': coords[0],
        'Formation Energy (meV/atom)': coords[1] * energy_mult,
        "Energy above hull (meV/atom)": phd.get_e_above_hull(entry) * energy_mult,
        'Formula': "C" if np.isclose(coords[0], 0) else f"{ion_element}C{int((1 - coords[0])/coords[0])}"
    } for entry, coords in unstable_entries.items() if phd.get_e_above_hull(entry) is not None and phd.get_e_above_hull(entry) < show_unstable]
    # Now, append all stable points to the same unstable_data
    stable_data = [{
        'ID': str(entry.data.get("ID")),
        'Energy': entry.energy_per_atom,
        'Concentration': coords[0],
        'Formation Energy (meV/atom)': coords[1] * energy_mult,
        "Energy above hull (meV/atom)": phd.get_e_above_hull(entry) * energy_mult,
        'Formula': "C" if np.isclose(coords[0], 0) else f"{ion_element}C{int((1 - coords[0])/coords[0])}"
    } for coords, entry in stable_entries.items()]
    data.extend(stable_data)

    if data:
        df = pd.DataFrame(data)
        df.to_csv(data_file, index=False, sep=' ')
    print(f"All energies saved to {data_file}")
    if stable_data:
        df = pd.DataFrame(stable_data)
        df.to_csv(gs_data_file, index=False, sep=' ')
    print(f"GS energies saved to {gs_data_file}")
    if phd.all_entries:
        min_entries = []
        for _, group_iter in itertools.groupby(phd.all_entries, key=lambda e: e.composition.reduced_composition):
            group = list(group_iter)
            entry = min(group, key=lambda e: e.energy_per_atom)
            min_entries.append({
                'ID': str(entry.data.get("ID")),
                "Energy": entry.energy_per_atom,
                "Formation energy (meV/atom)": phd.get_form_energy_per_atom(entry) * energy_mult,
                "Energy above hull (meV/atom)": phd.get_e_above_hull(entry) * energy_mult,
                "Reduced formula": entry.reduced_formula,
            })
        df = pd.DataFrame(min_entries)
        df.to_csv(min_data_file, index=False, sep=' ')
        print(f'Min energies saved to {min_data_file}')
    
    # Set publication-quality style
    plt.style.use('default')
    # Adjust font sizes based on the provided font_size argument
    base_sz = font_size
    base_markersize = base_sz * 0.5
    edge_width = max(0.8, round(0.12 * base_sz, 2))
    plt.rcParams.update({
        'font.size': base_sz,
        'font.family': 'serif',
        'font.serif': ['Times New Roman', 'DejaVu Serif'],
        'mathtext.fontset': 'stix',
        'axes.labelsize': base_sz,
        'axes.titlesize': base_sz * 1.2,
        'axes.linewidth': 1.0,
        'lines.linewidth': 1.2,
        'lines.markersize': base_markersize,
        'xtick.labelsize': base_sz,
        'ytick.labelsize': base_sz,
        'legend.fontsize': base_sz,
        'figure.titlesize': base_sz * 1.2,
    })

    original_color = '#4daffa'  # Blue for original structures
    perturbed_color = '#fa4d4d'  # Red for perturbed structures
    # Plot unstable entries
    for entry, coords in unstable_entries.items():
        e_above_hull = phd.get_e_above_hull(entry)
        if e_above_hull is not None and e_above_hull < show_unstable:
            # print(f"metastable:: {entry.data}, {coords[0]}, {coords[1]}")
            ax.plot(coords[0], np.array(coords[1]) * energy_mult, 's',
                    markerfacecolor=perturbed_color
                    if entry.data.get('is_extra', False)
                    else original_color,
                    markeredgecolor='black',
                    markeredgewidth=edge_width,
                    alpha=0.7)

    # Plot the phase boundaries
    for x, y in lines:
        ax.plot(x, np.array(y) * energy_mult, 'k-', linewidth=1.2)

    original_color_gs = '#00af00'
    perturbed_color_gs = original_color_gs
    # Plot stable entries
    for coords in stable_entries:
        entry = stable_entries[coords]
        print(f"GS:: {entry.data}, {coords[0]}, {coords[1]}")
        ax.plot(coords[0], np.array(coords[1]) * energy_mult, 'o', 
                markerfacecolor=perturbed_color_gs
                if entry.data.get('is_extra', False)
                else original_color_gs,
                markeredgecolor='black',
                markersize=base_markersize * 1.8,
                markeredgewidth=edge_width)

    # Add legend for stable and unstable entries with dual colors
    from matplotlib.lines import Line2D
    from matplotlib.legend_handler import HandlerTuple
    
    # Create single‑shape markers for the two “base” categories
    ground_state_marker = Line2D(
        [], [], marker='o', color='none',
        markerfacecolor=original_color_gs,   # original (stable) colour
        markeredgecolor='black',
        markersize=base_markersize * 1.8)

    above_hull_marker = Line2D(
        [], [], marker='s', color='none',
        markerfacecolor=original_color,   # original (unstable) colour
        markeredgecolor='black')

    original_perturbed_dual = (
        Line2D(
            [], [], marker='s', color='none',
            markerfacecolor=original_color,
            markeredgecolor=None,
            markersize=base_markersize),

        Line2D(
            [], [], marker='s', color='none',
            markerfacecolor=perturbed_color,
            markeredgecolor=None,
            markersize=base_markersize),
    )

    legend_handles = [
        ground_state_marker,
        above_hull_marker,
        original_perturbed_dual,
    ]
    
    ax.legend(handles=legend_handles, 
              labels=['Ground state', 'Above hull', 'Original/Perturbed'],
              handler_map={tuple: HandlerTuple(ndivide=None)},
              loc='best', fontsize=font_size)
    
    # Calculate center for label positioning
    min_y = min(c[1] for c in stable_entries)
    center = (0.5, min_y / 2)
    
    # Custom font for labels (overriding pymatgen's hardcoded 24pt bold)
    font = FontProperties()
    font.set_size(base_sz)
    font.set_weight('bold')

    # Add labels for stable entries
    for coords in sorted(stable_entries, key=lambda x: -x[1]):
        entry = stable_entries[coords]

        # Skip elemental references as they're handled separately
        if entry.composition.is_element:
            continue

        raw_label = entry.name
        label = _to_subscript(raw_label)

        # Calculate offset from center
        offset_radius_pt = base_sz * 1.5          # e.g. 9.6 pt for a base size of 8 pt
        vec = np.array(coords) - center
        norm = np.linalg.norm(vec)
        if norm != 0:
            vec = vec / norm * offset_radius_pt
        else:
            vec = np.zeros_like(vec)

        valign = "bottom" if vec[1] > 0 else "top"
        if vec[0] < -0.01:
            halign = "right"
        elif vec[0] > 0.01:
            halign = "left"
        else:
            halign = "center"

        ax.annotate(
            label,
            [coords[0], coords[1] * energy_mult],
            xytext=vec,
            textcoords="offset points",
            horizontalalignment=halign,
            verticalalignment=valign,
            fontproperties=font,
            color='black'
        )
    
    # Add elemental labels with proper positioning
    elem_font_size = base_sz * 1.2
    elem_font = FontProperties(size=base_sz+2, weight='bold')
    for coords in stable_entries:
        entry = stable_entries[coords]
        if entry.composition.is_element:
            elem_symbol = str(entry.elements[0])

            elem_offset_pt = elem_font_size
            # Position elemental labels at the edges
            if coords[0] < 0.1:
                # Left side - matrix element
                ax.annotate(matrix_element, 
                            [coords[0], coords[1] * energy_mult], 
                            xytext=(-elem_offset_pt, 0),
                            textcoords="offset points",
                            horizontalalignment="right",
                            verticalalignment="center",
                            fontproperties=elem_font)
            elif coords[0] > 0.9:
                # Right side - ion element
                ax.annotate(ion_element, 
                            [coords[0], coords[1] * energy_mult], 
                            xytext=(elem_offset_pt, 0),
                            textcoords="offset points",
                            horizontalalignment="left",
                            verticalalignment="center",
                            fontproperties=elem_font)

    # Set axis labels and limits
    ax.set_xlabel(f'{ion_element} Concentration')
    ax.set_ylabel('Formation Energy (meV/atom)')
    ax.set_title(title if title is not None else f'{ion_element}-{matrix_element} Phase Diagram', pad=20)
    
    # Set proper axis limits based on max_conc
    ax.set_xlim(-0.05, max_conc + 0.05)
    
    # Calculate y limits from stable entries with padding
    all_y = [c[1] * energy_mult for c in stable_entries] +\
        [c[1] * energy_mult for _, c in unstable_entries.items()]
    y_min = min(all_y)
    y_max = max(all_y)
    # Use manual limits if provided, otherwise apply padded limits
    if ymin is not None and ymin < y_min:
        y_min = ymin
    if ymax is not None:
        y_max = ymax
    # Apply padding (same factor as before)
    y_padding = (y_max - y_min) * 0.1
    ax.set_ylim(y_min - y_padding, y_max + y_padding)

    # Improve grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Add vertical line for IonC6 concentration
    ionc6_concentration = 1/7
    plt.axvline(x=ionc6_concentration, color='black', linewidth=1, linestyle='--', alpha=0.7)
    # Add annotation for IonC6 - positioned 1.5em to the right and just above x-axis
    plt.annotate(f'{ion_element}C$_{6}$',
                 xy=(ionc6_concentration, ax.get_ylim()[0]),
                 xytext=(base_sz * 1, base_sz * 0.5),
                 textcoords='offset points',
                 ha='left', va='bottom', font=elem_font,
                 color='black')


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
        "--max_composition",
        help="Maximum composition for the concentration axis (e.g. LiC2). "
        "If not specified, uses pure ion element as maximum.",
        type=Composition)


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
    parser.add_argument(
        "--dpi", default=600,
        help="Output DPI for publication quality (default: 300)",
        type=int)
    parser.add_argument(
        "--format", default="png",
        help="Output format (default: png, options: png, pdf, svg)",
        choices=["png", "pdf", "svg"])
    parser.add_argument(
        "--show_unstable", default=0.2,
        help="Show unstable entries with energy above hull less than this value (eV/atom) (default: 0.2)",
        type=float)
    parser.add_argument(
        "--font_size", default=DEFAULT_FONT_SIZE,
        help=f"Base font size for the plot (default: {DEFAULT_FONT_SIZE})",
        type=int)
    parser.add_argument(
        "--title", default=None,
        help="Custom title for the phase diagram plot (default: '<ion>-<matrix> Phase Diagram')",
        type=str)
    parser.add_argument(
        "--ymin",
        help="Manual y-axis minimum (in meV/atom).",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--ymax",
        help="Manual y-axis maximum (in meV/atom).",
        type=float,
        default=None,
    )
    parser.add_argument(
        "--entropy",
        help="When set, attempt reading mc_T300K_F_vs_c.dat file to extract entropies.",
        type=bool,
        action="store_true"
    )
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

    # Create figure with better aspect ratio
    fig, ax = plt.subplots(figsize=(4.13, 3)) # half A4

    path = Path('.')
    print(f"Extra paths: {args.extra_data}")
    entries = get_entries_recursively(
        Path(path), args.extra_data, args.extra_data_threshold)
    mc_data = Path('mc_T300K_F_vs_c.dat')
    if args.entropy and mc_data.is_file():
        df = pd.read_csv(
            mc_data, header=None, sep='\t',
            names=['c', 'F', 'mu', 'x', 'E'])
        print('Adding entropy adjustments')
        for entry in entries:
            atomic_fraction = entry.composition.get_atomic_fraction(args.ion)
            c = 2*atomic_fraction / (1 - atomic_fraction)
            closest_idx = (df['c'] - c).abs().idxmin()
            assert np.abs(df.loc[closest_idx]['c'] - c) < 0.01
            ts = df.loc[closest_idx]['E'] - df.loc[closest_idx]['F']
            entry.correction = -ts
    # entries = []
    # for c, E, F in zip(df['c'].values, df['E'].values, df['F'.values]):
    #     comp = Composition(f'{str(args.ion)}{c}{str(c_entry.composition)}')
    #     entry = ComputedEntry(comp, F)
    #     entry.data["volume"] = c_entry.data["volume"]
    #     entry.data["ID"] = None
    #     entry.data["is_extra"] = False
    #     entries.append(entry)
    
    phd = PhaseDiagram(entries=entries + [li_entry, c_entry], 
                      elements=[Element("C"), args.ion])
    
    # Use custom plotting function instead of pymatgen's get_plot
    plot_custom_phase_diagram(
        phd, ax, str(args.ion), "C",
        show_unstable=args.show_unstable,
        max_conc=args.max_composition.get_atomic_fraction(Element(args.ion)) if args.max_composition else 1.0,
        font_size=args.font_size,
        title=args.title,
        ymax=args.ymax,
        ymin=args.ymin)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save with publication quality settings
    output_file = [f'formation_en.{args.format}']
    if not args.format == "svg":
        output_file.append('formation_en.svg')
    for output in output_file:
        plt.savefig(output, dpi=args.dpi, bbox_inches='tight', 
                    facecolor='white', edgecolor='none')
    plt.close()

    print(f"Formation energy profile saved to {output_file}")

if __name__ == "__main__":
    main()
