import os
import shutil
from pymatgen.io.vasp.inputs import Incar, Kpoints, Poscar
from pymatgen.symmetry.bandstructure import HighSymmKpath

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
        print(f"Skipping {subfolder_path}: Not a directory.")
        continue  # Skip if not a directory
    
    for sub_subfolder in os.listdir(subfolder_path):
        sub_subfolder_path = os.path.join(subfolder_path, sub_subfolder)
        
        Relax_folder = os.path.join(sub_subfolder_path, 'Relax')
        BAND_folder = os.path.join(sub_subfolder_path, 'BAND')
        
        if os.path.isdir(sub_subfolder_path):  # Check if it's a directory
            # Proceed only if Relax_folder exists
            if os.path.exists(Relax_folder):
                # Create BAND_folder if it does not exist
                if not os.path.exists(BAND_folder):
                    os.mkdir(BAND_folder)
                    print(f"Created BAND folder at {BAND_folder}")
                
                src_contcar = os.path.join(Relax_folder, 'CONTCAR')  # Source CONTCAR
                dst_poscar = os.path.join(BAND_folder, 'POSCAR')      # Destination POSCAR in BAND folder
                
                # Copy CONTCAR to POSCAR within BAND folder if CONTCAR exists
                if os.path.exists(src_contcar):
                    shutil.copy(src_contcar, dst_poscar)
                    print(f"Copied CONTCAR to {dst_poscar}")
                else:
                    print(f"CONTCAR file not found in {Relax_folder}. Skipping {sub_subfolder_path}.")
                    continue  # Skip to next sub_subfolder if CONTCAR does not exist
                
                poscar_file = dst_poscar  # POSCAR in BAND_folder
                
                if os.path.exists(poscar_file):  # Check if POSCAR file exists in the BAND folder
                    # Read the POSCAR file
                    poscar = Poscar.from_file(poscar_file)
                    structure = poscar.structure
                
                    # Generate INCAR with SCAN functional and NCORE set to 16
                    incar = Incar({
                        'SYSTEM': f'{sub_subfolder}',
                        'ENCUT': 500,
                        'ICHARG': 2,
                        'LORBIT': 11,
                        'METAGGA': 'SCAN',       # Correctly set METAGGA to SCAN
                        'ISPIN': 2,
                        'EDIFF': 1e-6,
                        'NSW': 0,
                        'LASPH': True,
                        'NCORE': 16,             # Set NCORE to 16 for parallelization
                        'LWAVE': False,
                        'LCHARG': False
                    })
    
                    # Generate KPOINTS for high-symmetry path
                    try:
                        kpath = HighSymmKpath(structure)
                        kpoints = Kpoints.automatic_linemode(kpath.get_kpoints(line_density=40))
                    except Exception as e:
                        print(f"Error generating KPOINTS for {sub_subfolder_path}: {e}")
                        continue  # Skip to next sub_subfolder in case of error
    
                    # Define file paths for INCAR and KPOINTS within BAND folder
                    incar_file = os.path.join(BAND_folder, 'INCAR')
                    kpoints_file = os.path.join(BAND_folder, 'KPOINTS')
                
                    # Write the INCAR and KPOINTS files using get_string() for proper formatting
                    write_file_unix(incar_file, str(incar))
                    write_file_unix(kpoints_file, str(kpoints))
    
                    # Optionally, copy other necessary files (e.g., POTCAR)
                    # shutil.copy('path_to_POTCAR', BAND_folder)
    
                    print(f"INCAR and KPOINTS have been generated for {BAND_folder} using SCAN functional.")
                else:
                    print(f"POSCAR file not found in {BAND_folder}.")
            else:
                print(f"Relax folder does not exist in {sub_subfolder_path}. Skipping.")
        else:
            print(f"Skipping {sub_subfolder_path}: Not a directory.")
