"""
Use genetic algorithm to find GS structures.
Expect the structures to be stored in ATAT folder structure in current directory.
Each ATAT folder (0, 1, 10, ...) should have sub-folder ATAT and optionally ATAT.SCF.
Each sub-folder may have file "generation" storing a single number - generation number.
No such file implies generation 0.

The data fill be grouped according to number of Na in structures.
Each group will be converged separately.

1. Read all the generation 0 structures from <number>/ATAT folders (before relaxation)
2. Converge population 0 running VASP relaxation in ATAT folders -> SCF in ATAT.SCF
3. create new generations; converge, until min number of generations is reached
4. repeat until new generation does not bring improvements.
"""
from IMDgroup.pymatgen.io.vasp.vaspdir import IMDGVaspDir

def read_generation_0():
    """Read all <number>/ATAT initial structures.
    Return a dict gen0[<number of Na>] with all the
    structures.
    """
    vaspdirs = IMD



