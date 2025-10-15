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
import numpy as np
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


def get_entries_recursively(path: Path, extra_data: list[Path] | None = None) -> list:
    """Scan PATH for energies and return a list of computed entries.
    EXTRA_DATA is a list of relative directories to be scanned in addition to
    PATH.
    """
    # Collect all computed entries
    entries = []
    if extra_data is None:
        extra_data = []
    all_dirs = [Path(path)] + [Path(path) / Path(p) for p in extra_data]

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
    return entries


DEFAULT_FONT_SIZE = 8

def plot_custom_phase_diagram(
        phd, ax, ion_element, matrix_element,
        max_conc=1.0, show_unstable=0.2,
        font_size=DEFAULT_FONT_SIZE, title=None, ymin=None, ymax=None):
    """Custom phase diagram plot that overrides pymatgen's hardcoded font settings."""
    
    # Create a PDPlotter to access the plotting data
    plotter = PDPlotter(phd, show_unstable=show_unstable)
    lines, stable_entries, unstable_entries = plotter.pd_plot_data
    all_stable_en = [c[1] for c in stable_entries]
    all_unstable_en = [c[1] for _, c in unstable_entries.items()]
    print(f"Stable: {len(stable_entries)} ({min(all_stable_en)}..{max(all_stable_en)}eV); Unstable: {len(unstable_entries)} ({min(all_unstable_en)}..{max(all_unstable_en)}eV)")
    
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

    energy_mult = 1000
    # Plot unstable entries
    for entry, coords in unstable_entries.items():
        e_above_hull = phd.get_e_above_hull(entry)
        if e_above_hull is not None and e_above_hull < show_unstable:
            ax.plot(coords[0], np.array(coords[1]) * energy_mult, 's', 
                    markerfacecolor='#ff7f00', 
                    markeredgecolor='black',
                    markeredgewidth=edge_width,
                    alpha=0.7)

    # Plot the phase boundaries
    for x, y in lines:
        ax.plot(x, np.array(y) * energy_mult, 'k-', linewidth=1.2)

    # Plot stable entries
    for coords in stable_entries:
        entry = stable_entries[coords]
        ax.plot(coords[0], np.array(coords[1]) * energy_mult, 'o', 
                markerfacecolor='#4daf4a', 
                markeredgecolor='black',
                markersize=base_markersize * 1.8,
                markeredgewidth=edge_width)
    

    # Add legend for stable and unstable entries
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([], [], marker='o', color='none', markerfacecolor='#4daf4a',
               markeredgecolor='black', label='Ground state'),
        Line2D([], [], marker='s', color='none', markerfacecolor='#ff7f00',
               markeredgecolor='black', label='Above hull')
    ]
    ax.legend(handles=legend_handles, loc='best', fontsize=font_size)
    
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
    
    # Set proper axis limits
    # Set proper axis limits based on max_conc
    ax.set_xlim(-0.05, max_conc + 0.05)
    
    # # Adjust x‑ticks: ensure the maximum composition appears as the last tick.
    # # Preserve existing ticks and add the max_conc tick if it is not already present.
    # existing_xticks = list(ax.get_xticks())
    # if max_conc not in existing_xticks:
    #     existing_xticks.append(max_conc)
    # # Sort ticks for a tidy axis.
    # new_xticks = sorted(existing_xticks)
    # ax.set_xticks(new_xticks)
    # # Prepare tick labels: use the provided max_comp_label for the max_conc tick,
    # # otherwise default to a formatted number.
    # new_xtick_labels = []
    # past_max_label = False
    # for tick in new_xticks:
    #     if max_comp_label is not None and np.isclose(tick, max_conc):
    #         new_xtick_labels.append(str(max_comp_label))
    #         past_max_label = True
    #     elif past_max_label:
    #         new_xtick_labels.append("")
    #     else:
    #         # Remove trailing zeros for cleaner appearance.
    #         if tick.is_integer():
    #             new_xtick_labels.append(str(int(tick)))
    #         else:
    #             new_xtick_labels.append(f"{tick:.2f}")
    # ax.set_xticklabels(new_xtick_labels)

    # Calculate y limits from stable entries with padding
    all_y = [c[1] * energy_mult for c in stable_entries] +\
        [c[1] * energy_mult for _, c in unstable_entries.items()]
    y_min = min(all_y)
    y_max = max(all_y)
    # Apply padding (same factor as before)
    y_padding = (y_max - y_min) * 0.1
    # Use manual limits if provided, otherwise apply padded limits
    if ymin is not None:
        y_min = ymin
        y_padding = 0
    if ymax is not None:
        y_max = ymax
        y_padding = 0
    ax.set_ylim(y_min - y_padding, y_max + y_padding)

    # Improve grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)


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

    # Create figure with better aspect ratio
    fig, ax = plt.subplots(figsize=(4.13, 3)) # half A4

    path = Path('.')
    entries = get_entries_recursively(Path(path), args.extra_data)
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
    output_file = f'formation_en.{args.format}'
    plt.savefig(output_file, dpi=args.dpi, bbox_inches='tight', 
                facecolor='white', edgecolor='none')
    plt.close()

    print(f"Formation energy profile saved to {output_file}")

if __name__ == "__main__":
    main()
