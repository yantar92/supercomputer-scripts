#!/usr/bin/env python
# Read path from command line argument
# Compare dates of {path}/ATAT/CONTCAR and {path}/ATAT.SCF/CONTCAR files
# If ATAT/CONTCAR is modified _after_ ATAT.SCF/CONTCAR print message
import sys
import os
from datetime import datetime

path = sys.argv[1]
file1 = os.path.join(path, 'ATAT', 'CONTCAR')
file2 = os.path.join(path, 'ATAT.SCF', 'CONTCAR')
if not os.path.isfile(file1) or not os.path.isfile(file2):
        sys.exit(0)
time1 = os.path.getmtime(file1)
time2 = os.path.getmtime(file2)

if time1 > time2:
        print(f"{file1} has been modified after{file2}")


