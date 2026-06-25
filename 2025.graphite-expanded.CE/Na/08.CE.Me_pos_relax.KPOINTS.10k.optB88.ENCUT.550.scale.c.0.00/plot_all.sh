#!/usr/bin/env bash
FORMAT="png"
# Scale
echo $(pwd) | grep Li && ion="Li" || ion="Na"
if [[ "$ion" == "Na" ]]; then
    ymin="-25"
    ymax="100"
else
    ymin="-45"
    ymax="45"
fi
for stacking in AA AB; do
    for functional in optB88-vdW optB86b-vdW PBE+D2 vdW-DF vdW-DF2; do
	if [[ "$functional" == "optB88-vdW" ]]; then
	    functional_path="."
	    me_path="../../../00.reference/*.KPOINTS.10000.$functional.ENCUT.550.SCF"
        else
	    functional_path="$functional"
	    me_path="../../../../00.reference/*.KPOINTS.10000.$functional.ENCUT.550.SCF"
        fi
	for d in 3.75 3.99 4.25 4.58; do
	    (cd "${stacking}/d.${d}/$functional_path";
	     echo "${stacking}/d.${d}/$functional_path"
	     ~/data/2025.graphite-expanded.CE/atat-formation-energies.py --entropy_vibrational --entropy ../d.3.75/mc_T300K.out --format=${FORMAT} --ymin=${ymin} --ymax=${ymax} --title="${ion}-C (${stacking}) phase diagram. d=${d}A scaled; ${functional}"  --max_composition="${ion}C3" --ion ${ion} $me_path ./0/ATAT.SCF
	     # ~/data/2025.graphite-expanded.CE/atat-formation-energies.py --format=${FORMAT} --ymin=${ymin} --ymax=${ymax} --title="${ion}-C (${stacking}) phase diagram. d=${d}A scaled; ${functional}"  --max_composition="${ion}C3" --ion ${ion} $me_path ./0/ATAT.SCF --extra_data perturb*
             echo $IMAGES
	    )
	done
    done
done
module load GCCcore ImageMagick
find . -mindepth 2 -maxdepth 2 -type d | while read d; do
    (cd $d;
     montage formation_en.png */formation_en.png -tile 2x -geometry +0+0 formation_en_summary.png
    )
done

