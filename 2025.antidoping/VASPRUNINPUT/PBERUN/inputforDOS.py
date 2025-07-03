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
    
    # Ensure the subfolder is a directory
    if not os.path.isdir(subfolder_path):
        print(f"Skipping {subfolder_path}: Not a directory.")
        continue
    
    for sub_subfolder in os.listdir(subfolder_path):
        sub_subfolder_path = os.path.join(subfolder_path, sub_subfolder)
        Relax_folder = os.path.join(sub_subfolder_path, 'Relax')
        DOS_folder = os.path.join(sub_subfolder_path, 'DOS')
        
        # Check if sub_subfolder_path is a directory
        if not os.path.isdir(sub_subfolder_path):
            print(f"Skipping {sub_subfolder_path}: Not a directory.")
            continue
        
        # Proceed only if Relax folder exists
        if os.path.exists(Relax_folder):
            # Create DOS folder if it does not exist
            if not os.path.exists(DOS_folder):
                try:
                    os.mkdir(DOS_folder)
                    print(f"Created DOS folder: {DOS_folder}")
                except Exception as e:
                    print(f"Failed to create DOS folder {DOS_folder}: {e}")
                    continue  # Skip to the next sub_subfolder if folder creation fails
            
            src_contcar = os.path.join(Relax_folder, 'CONTCAR')  # Source CONTCAR
            dst_poscar = os.path.join(DOS_folder, 'POSCAR')      # Destination POSCAR
            
            # Copy CONTCAR to DOS/POSCAR if CONTCAR exists
            if os.path.exists(src_contcar):
                try:
                    shutil.copy(src_contcar, dst_poscar)
                    print(f"Copied {src_contcar} to {dst_poscar}")
                except Exception as e:
                    print(f"Failed to copy {src_contcar} to {dst_poscar}: {e}")
                    continue  # Skip to the next sub_subfolder if copy fails
            else:
                print(f"CONTCAR file not found in {Relax_folder}")
                continue  # Skip to the next sub_subfolder if CONTCAR is missing
            
            poscar_file = dst_poscar  # DOS/POSCAR
            
            # Check if POSCAR exists in DOS folder
            if os.path.exists(poscar_file):
                try:
                    # Read the POSCAR file
                    poscar = Poscar.from_file(poscar_file)
                    structure = poscar.structure
                    
                    # Generate INCAR without GGA and vdW-specific parameters, using NCORE instead of NPAR
                    incar = Incar({
                        'SYSTEM': f'{sub_subfolder}',
                        'ENCUT': 500,
                        'NEDOS': 20000,
                        'ISPIN': 2,
                        'ICHARG': 2,
                        'LORBIT': 11,
                        'EDIFF': 1e-6,
                        'NSW': 0,
                        'LASPH': True,
                        'NCORE': 16,       # Replaced 'NPAR': 4 with 'NCORE': 16
                        'LWAVE': False,
                        'LCHARG': False
                    })
                    
                    # Generate KPOINTS with 1000 points per reciprocal atom and gamma-centered
                    kpoints = Kpoints.automatic_density(structure, 10000, force_gamma=True)
                    
                    # Define file paths for INCAR and KPOINTS
                    incar_file = os.path.join(DOS_folder, 'INCAR')
                    kpoints_file = os.path.join(DOS_folder, 'KPOINTS')
                    
                    # Write the INCAR and KPOINTS files
                    write_file_unix(incar_file, str(incar))
                    write_file_unix(kpoints_file, str(kpoints))
                    
                    print(f"INCAR and KPOINTS have been generated for {DOS_folder}")
                except Exception as e:
                    print(f"Error processing {poscar_file}: {e}")
            else:
                print(f"POSCAR file not found in {DOS_folder}")
        else:
            print(f"Relax folder does not exist in {sub_subfolder_path}. Skipping.")
