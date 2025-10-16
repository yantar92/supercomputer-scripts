#!/bin/bash                             
                                        
#BSUB -J diamond                        # Job name
#BSUB -o job.%J.out                     # Name of stdout output file (%j expands to jobId)
#BSUB -q hpc                            # Name of the partition
#BSUB -R "span[hosts=1]"                # Don't spread the CPU's across nodes
#BSUB -R rusage[mem=2GB]                # How much memory is required per core?
#BSUB -n 8                              # Total number of mpi tasks requested
#BSUB -W 01:30                          # Run time (hh:mm:ss) - 1.5 hours
                                        
# Launch MPI-based executable           
                                        
echo "Starting run at: `date`"          
                                        
source /dtu/sw/dcc/dcc-sw.bash
module load intel/2020.4.304
module load intel/2020.4.304.mpi

unset I_MPI_SHM_LMT
unset I_MPI_FABRICS_LIST
export I_MPI_FABRICS=shm
                                        
                                        
mpirun /zhome/43/5/58576/vasp/vasp.6.3.2/bin/vasp_std > vasp.out
                                        
rm CHG CHGCAR DOSCAR EIGENVAL IBZKPT PCDAT PROCAR REPORT vasprun.xml WAVECAR XDATCAR
                                        
echo "Job finished at: `date`"          
                                        
