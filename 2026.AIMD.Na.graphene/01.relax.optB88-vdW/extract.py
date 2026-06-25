import sys
from pathlib import Path
from pymatgen.io.vasp import Xdatcar
from IMDgroup.pymatgen.io.vasp.inputs import Incar
from pymatgen.io.vasp.inputs import Kpoints
from IMDgroup.pymatgen.io.vasp.sets import IMDStandardVaspInputSet_relax

source = Path(sys.argv[1])
assert source.is_dir()

incar = Incar.from_file(source / 'INCAR')
xd = Xdatcar(source / 'XDATCAR')
potim = incar['POTIM']
assert potim > 0

target_time = 10 # 30 fs
n_structures = int(target_time / potim)
print(f"The number of structures in XDATCAR: {len(xd.structures)}")
assert len(xd.structures) > n_structures

last_structures = xd.structures[-n_structures:]

vset = IMDStandardVaspInputSet_relax(
    functional='optB88-vdW',
    user_incar_settings={
        "ENCUT": 450,
        "IBRION": Incar.IBRION_IONIC_RELAX_CGA,
        'ISIF': Incar.ISIF_RELAX_POS_FAST,
        'EDIFFG': -0.05,
        # With Normal, getting subspacematrix errors
        'PREC': 'Accurate',
        'ISPIN': 1,
        'ALGO': 'Normal',
        'NELM': 200,
    },
)

for idx, struct in enumerate(last_structures):
    vset.structure = struct
    d = Path(f"{source.name}.relax.ISPIN.1/{idx}.relax/")
    vset.write_input(d)
    Kpoints(kpts=[(2, 2, 1)]).write_file(d / "KPOINTS")

