import sys
import re
from pathlib import Path
import pymatgen.core as pmg
from pymatgen.io.vasp.outputs import Vasprun
from IMDgroup.pymatgen.core.structure import reduce_supercell
from IMDgroup.pymatgen.io.vasp.sets import IMDDerivedInputSet

# arg = "graphite.AB.6x6x4/strain.c.0.00"
input_dir_ab1 = Path(sys.argv[1]) / Path("AB1")
# input_dir_ab2 = Path(sys.argv[1]) / Path("AB2")
m = re.search(r'strain[^/]+', str(input_dir_ab1))
assert m is not None
output_dir = Path('01.AB1.CE') / Path(m.group())

run = Vasprun(input_dir_ab1 / 'vasprun.xml')
struct_ab1 = run.final_structure
# run = Vasprun(input_dir_ab2 / 'vasprun.xml')
# struct_ab2 = run.final_structure
struct2 = struct_ab1.copy()
struct2.remove_species(['Na'])
struct3 = reduce_supercell(struct2)
prototype = struct3.copy()

Na_AB1_site = struct_ab1[struct_ab1.species.index(pmg.Element('Na'))]
# Na_AB2_site = struct_ab2[struct_ab2.species.index(pmg.Element('Na'))]

# , Na_AB2_site
for site in [Na_AB1_site]:
    struct3.insert(
        0,
        species=site.species,
        coords=site.coords,
        coords_are_cartesian=True,
    )

from IMDgroup.pymatgen.transformations.symmetry_clone import SymmetryFillTransformation
trans = SymmetryFillTransformation(prototype, ['Na'])
struct3 = trans.apply_transformation(struct3)

# NCORE = 16 will fail for too small supercells.
# artifically increase the initial cell size
# it actualy makes VASP *faster* on cluster
# struct3 *= [2, 2, 1]

struct3.add_site_property(
    "selective_dynamics",
    [[True, True, True] if s.specie == pmg.Element('Na')
     else [True, True, False] for s in struct3]
    )

inputset = IMDDerivedInputSet(
    directory=input_dir_ab1,
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

inputset.poscar.write_file(output_dir / "POSCAR")

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
