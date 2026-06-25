#!/usr/bin/env bash
get_ids() {
    for file in $(cd ..; find . -maxdepth 2 -iname "str.out"); do
	echo "$(dirname "$file")"
    done | sort
}

# optB88-vdW PBE+TS
for functional in PBE+D2 vdW-DF vdW-DF2 optB86b-vdW; do
    mkdir -p $functional && cd $functional
    get_ids | while read x; do
        [[ -d "$x" ]] && continue;
        echo $x;
        mkdir $x && imdg derive ../$x/ATAT --output=$x/ATAT functional $functional;
        imdg derive $x/ATAT --output=$x/ATAT functional $functional;
        cp ../INCAR.* $x/ATAT/
    done
    get_ids | while read x; do [[ -f "$x/str.out" ]] && continue; cp ../$x/str.out $x/; done
    cd ..
done

