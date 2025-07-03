#!/usr/bin/env python
from pathlib import Path
import argparse

def parse_args():
    parser = argparse.ArgumentParser(
        description='Mark ATAT XXXX folders with >N atoms with error')
    parser.add_argument('maxatoms', help='Max numer of atoms')
    return parser.parse_args()

def main():
    args = parse_args()
    input_path = args.input
    output_path = args.output
    verbose = args.verbose

    if verbose:
        print(f"Reading from {input_path}")
        print(f"Writing to {output_path}")

    # TODO: Implement the core functionality here

if __name__ == "__main__":
    main()

for d in Path().iterdir():
    if d.is_dir() and (d / 'str.out').is_file():
        with open(d / 'str.out', 'r', encoding='utf-8') as f:
            n_Na = 0
            n_Vac = 0
            for line in f:
                if 'Vac' in line:
                    n_Vac += 1
                elif 'Na' in line:
                    n_Na += 1
            concentration = n_Na / (n_Na + n_Vac)
            if concentration > max_c and not (d / 'error').is_file():
                print(f'{d}: {concentration} marking with error')
                (d / 'error').touch()
                (d / 'marked_error').touch()
