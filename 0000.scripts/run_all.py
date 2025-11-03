#!/usr/bin/env python
import argparse
import os
import time
import subprocess
from contextlib import chdir
from IMDgroup.gorun.gorun_atat_local import main, get_args

max_jobs = 400
def jobs_submitted():
    submissions = subprocess.check_output(
        "squeue -u $USER -o %Z | tail -n +2",
        shell=True
    ).decode('utf-8').split()
    return len(submissions)


n_jobs = jobs_submitted()

parser = argparse.ArgumentParser(
    description="Run gorun-atat-local recursively")
parser.add_argument("--max_jobs", help="Max number of jobs allowed", type=int, default=max_jobs)
parser.add_argument("--nodes", help="Number of nodes", type=int, default=1)
parser.add_argument("--noperturb", help="When provided, skip nested perturb folders", action="store_true")
parser.add_argument("--mark", help="When provided, pass --mark to gorun", action="store_true")
args = parser.parse_args()
max_jobs = args.max_jobs
args.kpoints = 10000
args.frac_tol = 0
args.skip_relax = False
args.max_strain = 5.40
#args.sublattice_cutoff = 0.5
args.sublattice_cutoff = 0.1
if args.mark:
    args.vasp_command = ['gorun', str(args.nodes), '48:00:00', '--mark']
else:
    args.vasp_command = ['gorun', str(args.nodes), '48:00:00']
dir_list = []
for wdir, _, files in os.walk('.'):
    if 'str.out' in files and not ('energy' in files or 'error' in files or (args.noperturb and 'perturb' in wdir)):
        dir_list.append(wdir)
dir_list = sorted(dir_list)
for wdir in dir_list:
    if (not args.mark) and n_jobs >= max_jobs:
        n_jobs = jobs_submitted()
        if n_jobs >= max_jobs:
            print("run_all: Waiting for submitted jobs to finish")
        while n_jobs >= max_jobs:
            time.sleep(10)
            n_jobs = jobs_submitted()
    print(f"Submitting a job in {wdir}")
    with chdir(wdir):
        try:
            main(args)
        except Exception as e:
            print(e)
        n_jobs += 1
