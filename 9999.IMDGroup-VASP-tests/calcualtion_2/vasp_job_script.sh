#!/bin/bash
#SBATCH -J my_vasp
#SBATCH -N 2
#SBATCH -t 24:00:00
#SBATCH --partition=small
#SBATCH --mem=200G
#SBATCH --exclusive --no-requeue
#SBATCH -A project_465000701
#SBATCH --ntasks-per-node=128
#SBATCH -c 1
#SBATCH -o /pfs/lustrep2/projappl/project_465000701/oimalyi/vasp_test_data/no_LASPH/no_LASPH/restart_original_POSCAR_two_nodes/energy/vasp_%j.out
#SBATCH -e /pfs/lustrep2/projappl/project_465000701/oimalyi/vasp_test_data/no_LASPH/no_LASPH/restart_original_POSCAR_two_nodes/energy/vasp_%j.err

export OMP_NUM_THREADS=1

module load LUMI/23.09 partition/C
module load VASP/6.4.2-cpeGNU-23.09-build01
srun vasp_std
