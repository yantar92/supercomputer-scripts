#!/usr/bin/env bash
# %
FORMAT="png"
echo $(pwd) | grep Li && ion="Li" || ion="Na"
if [[ "$ion" == "Na" ]]; then
    ymin="-25"
    ymax="100"
else
    ymin="-45"
    ymax="45"
fi
ds=(3.52 3.99 4.58 3.52 3.99 4.58)
idx=0
find . -mindepth 2 -maxdepth 2 -type d | sort | while read d; do
    for functional in optB88-vdW optB86b-vdW PBE+D2 vdW-DF vdW-DF2; do
	if [[ "$functional" == "optB88-vdW" ]]; then
	    functional_path="."
	    me_path="../../../00.reference/*.KPOINTS.10000.$functional.ENCUT.550.SCF"
        else
	    functional_path="$functional"
	    me_path="../../../../00.reference/*.KPOINTS.10000.$functional.ENCUT.550.SCF"
        fi
	echo $d $idx ${ds[$idx]} $functional;
	(cd $d/$functional_path;
	 ~/data/2025.graphite-expanded.CE/atat-formation-energies.py --entropy ../mc_T300K.out --format=${FORMAT} --ymin=${ymin} --ymax=${ymax} --title="${ion}-C ($(dirname $d)) phase diagram. d=${ds[$idx]}A %; $functional"  --max_composition="${ion}C3" --ion ${ion} $me_path ./0/ATAT.SCF
	 # ~/data/2025.graphite-expanded.CE/atat-formation-energies.py --format=${FORMAT} --ymin=${ymin} --ymax=${ymax} --title="${ion}-C ($(dirname $d)) phase diagram. d=${ds[$idx]}A %; $functional"  --max_composition="${ion}C3" --ion ${ion} $me_path ./0/ATAT.SCF --extra_data perturb*
	)
    done
    idx=$(($idx + 1))
done
module load GCCcore ImageMagick
find . -mindepth 2 -maxdepth 2 -type d | while read d; do
    (cd $d;
     montage formation_en.png */formation_en.png -tile 2x -geometry +0+0 formation_en_summary.png
    )
done

