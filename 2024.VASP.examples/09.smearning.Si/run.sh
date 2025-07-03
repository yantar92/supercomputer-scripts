#!/usr/bin/env bash
# [[file:/home/yantar92/Org/notes.org::*Workflow][Workflow:1]]
mkdir -p si-smearing
cd si-smearing
~/groupdir/mp-input.py mp-149 # Si
cd ..
mkdir -p ni-smearing
cd ni-smearing
~/groupdir/mp-input.py mp-23 # Ni
cd ..

find ./ -mindepth 2 -maxdepth 2 -type d | while read x; do echo "$x"; cd "$x"; ~/groupdir/DOS-input.py --use-poscar True .; cd -; done

# args: command to be evaluated
loop-over-structures () {
    find ./ -type d -iname "*DOS*" |\
	while read x; do
	    echo "$x";
	    cd "$x";
	    $*;
	    cd -;
        done
}

# Need lower NCORE as the systems are very small

# ISMEAR=-5 ignores SIGMA; set it separately
loop-over-structures ~/groupdir/change-input.py --incar="ISMEAR:-5" --incar="NCORE:4" .;

# ISMEAR=0, 1 is sensitive to SIGMA, try different SIGMA values
for ISMEAR in 0 1; do
    for SIGMA in 0.01 0.02 0.03 0.04 0.05 0.06 0.08 0.10 0.12 0.15 0.20 0.25 0.30 0.40 0.50 1.0; do
	loop-over-structures ~/groupdir/change-input.py --incar="ISMEAR:$ISMEAR" --incar="SIGMA:$SIGMA" --incar="NCORE:4" .;
    done
done

find ./ -type d -iname "*ISMEAR*" | while read x; do echo "$x"; cd "$x"; gorun-helios 1 1:00:00; cd -; done
# Workflow:1 ends here
