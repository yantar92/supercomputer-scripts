import itertools
import hashlib
import sys
import numpy as np

def generate_voltage_points():
    """20 voltage points with higher density in 0-0.1V."""
    # low = np.linspace(0, 0.3, 30, endpoint=True)      # 10 points
    # mid = np.linspace(0.3, 1, 5, endpoint=False)      # 5 points (0.1 already in low)
    # high = np.linspace(1, 4, 5, endpoint=True)        # 5 points
    # voltages = np.unique(np.concatenate([low, mid, high]))
    voltages = [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1]
    return voltages


# defect_probabilities = [0, 0.174, 0.5]
# defect_probabilities = [0.174, 0.1, 0.09, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02]
temperatures = [1200, 2000, 3000, 4000]
# temperatures = np.arange(298, 2000, 10)
radiuses = np.arange(5, 31, 1)
# radiuses = [5, 7, 8, 10, 16, 20, 24, 30]
voltages = generate_voltage_points()
commands = []
for radius, voltage, temp in itertools.product(radiuses, voltages, temperatures):
    param_str = f"{voltage:.2f}V_{temp:.0f}K_{radius}A"
    seed = hashlib.md5(param_str.encode()).hexdigest()
    seed_int = int(seed[:8], 16)
    cmd = (f"python mc-pore.py --voltage {voltage}  --radius {radius} "
           f"--defect_probability 0 --csv --quiet --converge --file {param_str}.csv.gz "
           f"--steps 1000000 --seed {seed_int} --temp {temp}")
    # repeat 5 times
    commands.append(cmd)
    commands.append(cmd)
    commands.append(cmd)
    commands.append(cmd)
    commands.append(cmd)

with open('commands2.txt', 'w') as f:
    f.write('\n'.join(commands))
print(f"# To run: cat commands2.txt | parallel -j 96", file=sys.stderr)
