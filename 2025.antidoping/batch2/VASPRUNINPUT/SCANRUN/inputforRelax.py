import os
import shutil
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
        Relax_folder = os.path.join(sub_subfolder_path, 'Relax')
        
        if os.path.isdir(sub_subfolder_path):  # Check if it's a directory
            # Create Relax folder if it does not exist
            if not os.path.exists(Relax_folder):
                os.mkdir(Relax_folder)
                print(f"Created Relax folder at {Relax_folder}")
            
            src = os.path.join(sub_subfolder_path, 'CONTCAR')  # Source CONTCAR
            dst = os.path.join(Relax_folder, 'POSCAR')         # Destination POSCAR in Relax folder
            
            # Copy CONTCAR to POSCAR within Relax folder if CONTCAR exists
            if os.path.exists(src):
                shutil.copy(src, dst)
                print(f"Copied CONTCAR to {dst}")
            else:
                print(f"CONTCAR file not found in {sub_subfolder_path}")
                continue  # Skip to next sub_subfolder if CONTCAR does not exist
            
            poscar_file = os.path.join(Relax_folder, 'POSCAR')
        
            if os.path.exists(poscar_file):  # Check if POSCAR file exists in the Relax folder
                # Read the POSCAR file
                poscar = Poscar.from_file(poscar_file)
                structure = poscar.structure
            
                # Generate INCAR with SCAN functional and NCORE set to 16
                incar = Incar({
                    'SYSTEM': f'{sub_subfolder}',
                    'ENCUT': 500,
                    'ISIF': 2,
                    'METAGGA': 'SCAN',       # Correctly set METAGGA to SCAN
                    'ISPIN': 2,
                    'IBRION': 2,
                    'EDIFF': 1e-6,
                    'EDIFFG': -0.01,
                    'NSW': 100,
                    'LASPH': True,
                    'NCORE': 16,             # Set NCORE to 16 for parallelization
                    'LWAVE': False,
                    'LCHARG': False
                })
    
                # Generate KPOINTS with 1000 points per reciprocal atom and gamma-centered
                kpoints = Kpoints.automatic_density(structure, 10000, force_gamma=True)
            
                # Define file paths for INCAR and KPOINTS within Relax folder
                incar_file = os.path.join(Relax_folder, 'INCAR')
                kpoints_file = os.path.join(Relax_folder, 'KPOINTS')
            
                # Write the INCAR and KPOINTS files using get_string() for proper formatting
                write_file_unix(incar_file, str(incar))
                write_file_unix(kpoints_file, str(kpoints))
    
                # Optionally, copy other necessary files (e.g., POTCAR)
                # shutil.copy('path_to_POTCAR', Relax_folder)
    
                print(f"INCAR and KPOINTS have been generated for {Relax_folder} using SCAN functional.")
            else:
                print(f"POSCAR file not found in {Relax_folder}")
