#!/bin/bash

[[ ! -f error ]] && echo "No error found!" && exit 1
[[ -d gorun1 ]] && echo "gorun1 already present" && exit 1

mkdir gorun1
if [[ -f CONTCAR.relax && -s CONTCAR.relax ]]; then
    cp CONTCAR.relax gorun1/POSCAR
else
    rmdir gorun1
    echo "!!!! CONTCAR empty !!!! exiting" && exit 1
fi
cp KPOINTS.relax gorun1/KPOINTS
cp INCAR.relax gorun1/INCAR
cd gorun1
gorun 1 4:00:00 && cd .. || (cd ..; rm -rf gorun)
