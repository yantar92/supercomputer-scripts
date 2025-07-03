#!/usr/bin/env python
import argparse
import os
import time
import subprocess
from contextlib import chdir
from IMDgroup.gorun.gorun_atat_local import main, get_args

max_jobs = 100
def jobs_submitted():
    submissions = subprocess.check_output(
        "squeue -u $USER -o %Z | tail -n +2",
        shell=True
    ).decode('utf-8').split()
    return len(submissions)


n_jobs = jobs_submitted()

parser = argparse.ArgumentParser(
    description="Run gorun-atat-local recursively")
args = parser.parse_args()
args.kpoints = 10000
args.frac_tol = 0
args.skip_relax = True
args.vasp_command = ['gorun', '1', '1:00:00']
dir_list = []
for wdir, _, files in os.walk('.'):
    if 'str.out' in files and not ('energy' in files or 'error' in files):
        dir_list.append(wdir)
dir_list = sorted(dir_list)
for wdir in dir_list:
    if n_jobs >= max_jobs:
        n_jobs = jobs_submitted()
        if n_jobs >= max_jobs:
            print("Waiting for submitted jobs to finish")
        while n_jobs >= max_jobs:
            time.sleep(10)
            n_jobs = jobs_submitted()
    print(f"Submitting a job in {wdir}")
    with chdir(wdir):
        main(args)
        n_jobs += 1
