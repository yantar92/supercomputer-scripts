import os
import shutil
from pymatgen.ext.matproj import MPRester
from pymatgen.io.vasp.inputs import Incar, Kpoints, Poscar

# Define the main directory containing subfolders with POSCAR files
main_dir = './IBCANDIDATES'

# Function to write file with Unix line endings and UTF-8 encoding
def write_file_unix(file_path, content):
    with open(file_path, 'w', newline='\n', encoding='utf-8') as file:
        file.write(content)

# Loop through each subfolder in the main directory
for subfolder in os.listdir(main_dir):
    subfolder_path = os.path.join(main_dir, subfolder)
    if not os.path.isdir(subfolder_path):
        continue  # Skip if not a directory
    for sub_subfolder in os.listdir(subfolder_path):
        sub_subfolder_path = os.path.join(subfolder_path, sub_subfolder)
        if os.path.isdir(sub_subfolder_path):  # Check if it's a directory
            poscar_file = os.path.join(sub_subfolder_path, 'POSCAR')
        
            if os.path.exists(poscar_file):  # Check if POSCAR file exists in the subfolder
                # Read the POSCAR file
                poscar = Poscar.from_file(poscar_file)
                structure = poscar.structure
            
                # Generate INCAR with SCAN functional and NCORE set to 16
                incar = Incar({
                    'SYSTEM': f'{sub_subfolder}',
                    'ENCUT': 550,
                    'ISIF' : 3,
                    'METAGGA': 'SCAN',  # Correctly set METAGGA to SCAN
                    'ISPIN': 2,
                    'IBRION': 2,
                    'EDIFF': 1e-6,
                    'EDIFFG': -0.01,
                    'NSW': 100,
                    'LASPH': True,
                    'NCORE': 16,        # Set NCORE to 16 for parallelization
                    'LWAVE': False,
                    'LCHARG': False
                })

                # Generate KPOINTS with 1000 points per reciprocal atom and gamma-centered
                kpoints = Kpoints.automatic_density(structure, 1000, force_gamma=True)
            
                # Write the INCAR and KPOINTS files
                incar_file = os.path.join(sub_subfolder_path, 'INCAR')
                kpoints_file = os.path.join(sub_subfolder_path, 'KPOINTS')
            
                write_file_unix(incar_file, str(incar))
                write_file_unix(kpoints_file, str(kpoints))

                # Optionally, copy other necessary files (e.g., POTCAR)
                # shutil.copy('path_to_POTCAR', sub_subfolder_path)

                print(f"INCAR and KPOINTS have been generated for {sub_subfolder_path} using SCAN functional.")
            else:
                print(f"POSCAR file not found in {sub_subfolder_path}")
