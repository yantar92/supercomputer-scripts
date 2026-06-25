#!/usr/bin/env bash
# 1. Save the two scripts as mc-pore-scan.py and generate_scan.py
# 2. Install dependencies (if not already installed):
#    pip install numpy matplotlib pandas

# 3. Generate the command list (takes a few seconds):
# 1300 1400
for t in 2000 1900 1800 1700 1600 1500; do
  python generate_scan.py --converge --steps 1000000 --output commands.txt --temperature $t
  cat commands.txt | parallel -j 96 --line-buffer >> results.csv
done

# 4. Run with GNU Parallel on 96 cores:

# 5. After all jobs finish, you will have a single CSV file `results.csv`
#    with one row per simulation. You can load it with pandas for analysis.
