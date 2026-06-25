#!/usr/bin/env bash

# relax
FORMAT="png"
echo $(pwd) | grep Li && ion="Li" || ion="Na"
if [[ "$ion" == "Na" ]]; then
    ymin="-25"
    ymax="100"
else
    ymin="-45"
    ymax="45"
fi
find . -mindepth 2 -maxdepth 2 -type d | while read d; do
    for functional in optB88-vdW optB86b-vdW PBE+D2 vdW-DF vdW-DF2; do
	if [[ "$functional" == "optB88-vdW" ]]; then
	    functional_path="."
	    me_path="../../../00.reference/*.KPOINTS.10000.$functional.ENCUT.550.SCF"
        else
	    functional_path="$functional"
	    me_path="../../../../00.reference/*.KPOINTS.10000.$functional.ENCUT.550.SCF"
        fi
	echo $d/$functional_path;
	(cd $d/$functional_path;
	 ~/data/2025.graphite-expanded.CE/atat-formation-energies.py --format=${FORMAT} --ymin=${ymin} --ymax=${ymax} --title="${ion}-C ($(dirname $d)) phase diagram. d=relax; $functional"  --max_composition="${ion}C3" --ion ${ion} $me_path ./0/ATAT.SCF --extra_data perturb.*
	)
    done
done
module load GCCcore ImageMagick
find . -mindepth 2 -maxdepth 2 -type d | while read d; do
    (cd $d;
     montage formation_en.png */formation_en.png -tile 2x -geometry +0+0 formation_en_summary.png
    )
done

