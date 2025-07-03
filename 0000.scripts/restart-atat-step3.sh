#!/bin/bash

[[ ! -d gorun1 ]] && echo "No gorun1 found" && exit 1
[[ ! -d gorun1.SCF ]] && echo "No gorun1.SCF found" && exit 1

cd gorun1
cp CONTCAR ../CONTCAR.relax || exit 1
cp OSZICAR ../OSZICAR.relax
gzip OUTCAR
cp OUTCAR.gz ../OUTCAR.relax.gz
cp slurm* ../vasp.out.relax
cd ..

cd gorun1.SCF
cp CONTCAR ../CONTCAR.static || exit 1
cp POSCAR ../POSCAR.static
cp OSZICAR ../OSZICAR.static
gzip OUTCAR
cp OUTCAR.gz ../OUTCAR.static.gz
cp slurm* ../vasp.out.static
cp vasprun.xml ../vasprun.xml
cd ..

extract_vasp
rm error
touch ../refresh

