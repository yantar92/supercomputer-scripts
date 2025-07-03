import sys
import re
from pathlib import Path
import pymatgen.core as pmg
from pymatgen.io.vasp.outputs import Vasprun
from IMDgroup.pymatgen.core.structure import reduce_supercell
from IMDgroup.pymatgen.io.vasp.sets import IMDDerivedInputSet

# arg = "graphite.AA.6x6x4/strain.c.0.00/AA"
input_dir = Path(sys.argv[1])
m = re.search(r'strain[^/]+', str(input_dir))
assert m is not None
output_dir = Path('01.CE') / Path(m.group())

run = Vasprun(input_dir / 'vasprun.xml')
struct = run.final_structure
struct2 = struct.copy()
struct2.remove_species(['Na'])
struct3 = reduce_supercell(struct2)
Na_site = struct[struct.species.index(pmg.Element('Na'))]
struct3.insert(
    0,
    species = Na_site.species,
    coords = Na_site.coords,
    coords_are_cartesian=True,
)
struct3.add_site_property(
    "selective_dynamics",
    [[True, True, True] if s.specie == pmg.Element('Na')
     else [True, True, False] for s in struct3]
    )

# NCORE = 16 will fail for too small supercells.
# artifically increase the initial cell size
# it actualy makes VASP *faster* on cluster
# struct3 *= [2, 2, 1]

inputset = IMDDerivedInputSet(
    directory=input_dir,
    user_kpoints_settings={'grid_density': 10000}
)
inputset.structure = struct3

from pymatgen.io.atat import Mcsqs
atat_in = Mcsqs(inputset.structure)
atat_str = atat_in.to_str()
atat_str = re.sub(r'=1', '', atat_str)
atat_str = re.sub(r'Na', 'Na,Vac', atat_str)

if not output_dir.is_dir():
    output_dir.mkdir(parents=True)

with open(output_dir / "lat.in", mode='w', encoding='utf8') as f:
    f.write(atat_str)


incar_extra = """\
KPPRA = 10000
USEPOT = PAWPBE
SUBATOM = s/Na$/Na_sv T T T/g
SUBATOM = s/C$/C T T F/g
DOSTATIC
"""
with open(output_dir / "vasp.wrap", mode='w', encoding='utf8') as f:
    f.write(f"[INCAR]\n{inputset.incar}{incar_extra}")

with open(output_dir / "sub", mode='w', encoding='utf8') as f:
    f.write("""\
#!/usr/bin/bash
#SBATCH --nodes="1"
#SBATCH --time="48:00:00"
#SBATCH --ntasks-per-node="128"
#SBATCH --account="project_465001654"
#SBATCH --partition="small"
#SBATCH --job-name="LiC6.mp-1001581.hexagonal.191"

export EBU_USER_PREFIX=/projappl/project_465001654/dist/EasyBuild
module load LUMI/24.03 partition/C PrgEnv-gnu cray-fftw/3.3.10.7 OpenBLAS/0.3.24-cpeGNU-24.03  ScaLAPACK/4.2-cpeGNU-24.03-amd

maps -d &
sleep 5
pollmach runstruct_vasp srun
    """)
inputset.write_input(output_dir=output_dir)
