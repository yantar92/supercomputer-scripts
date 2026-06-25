#!/usr/bin/env bash
get_ids() {
    for file in $(cd ..; find . -maxdepth 2 -iname "str.out"); do
	echo "$(dirname "$file")"
    done | sort
}

for p in 0.1 0.2 0.4; do
    mkdir -p "perturb.$p" && cd "perturb.$p"
    get_ids | while read x; do
        [[ ! -d "../$x/ATAT" ]] && continue;
        [[ -d "$x" ]] && continue;
        echo $x;
        mkdir $x;
        cp ../$x/str.out $x/;
        imdg derive ../$x/ATAT --output=$x/ATAT perturb --distance=$p;
    done
    cd ..
done
#mkdir -p "perturb.0.4.2x2x2" && cd "perturb.0.4.2x2x2"
#get_ids | while read x; do
#    [[ -d "$x" ]] && continue
#    [[ ! -d "../$x/ATAT" ]] && continue
#    echo $x;
#    mkdir $x && imdg derive ../$x/ATAT --output=$x/ATAT/.source supercell 2x2x2;
#    imdg derive $x/ATAT/.source --output=$x/ATAT perturb --distance=0.4;
#    cp ../$x/str.out $x/;
#    cp $x/str.out $x/str.out.orig
#    python <<EOF
#import shutil
#from IMDgroup.pymatgen.core.structure import IMDStructure
#s = IMDStructure.from_file("$x/str.out")
#shutil.copyfile("$x/str.out", "$x/str.out.orig")
#s2 = s * 2
#s2.__class__ = IMDStructure
#s2.to_file("$x/str.out")
#EOF
#done
#cd ..
