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
    voltages = [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 3.0]
    return voltages


# defect_probabilities = [0, 0.174, 0.5]
defect_probabilities = [0.174]
# temperatures = [298]
temperatures = np.arange(298, 2000, 10)
# radiuses = np.arange(5, 31, 1)
radiuses = [5, 7, 8, 10, 16, 20, 24, 30]
voltages = generate_voltage_points()
all_steps = np.logspace(np.log10(10000), np.log10(100000000), 5)
commands = []
for prob, temp, radius, steps in itertools.product(defect_probabilities, temperatures, radiuses, all_steps):
    param_str = f"{prob:.3f}_{temp:.0f}_{radius}_{steps}"
    seed = hashlib.md5(param_str.encode()).hexdigest()
    seed_int = int(seed[:8], 16)
    cmd = (f"python mc-pore.py --voltage {' '.join(str(x) for x in reversed(voltages))}  --radius {radius} "
           f"--defect_probability {prob} --csv --quiet --converge "
           f"--steps {int(steps)} --seed {seed_int} --temp {temp}")
    commands.append(cmd)

with open('commands2.txt', 'w') as f:
    f.write('\n'.join(commands))
print(f"# To run: cat commands2.txt | parallel -j 96", file=sys.stderr)
