#!/bin/env bash
#SBATCH --job-name=gen-neb-input
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --time=72:00:00
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task 1
#SBATCH --partition=plgrid
root="04.NEB.sparse.interpolation"
mkdir -p "$root"

# Location of expanded graphite prototypes (without Na)
prototype="02.graphite-expanded.relax.RELAX_POS.POTIM.0.25"
# Location of relaxed unique graphite + Na structures
Na_loc="03.graphite-expanded.Na.uniq_sites"

# PBE+TS potential overbinds Na; no longer using it.
for potential in optB88-vdW; do
    mkdir -p "$root/$potential"
    #  graphite.AA.6x6x4 graphite.AB.6x6x2
    for system in graphite.AB.6x6x2; do
	mkdir -p "$root/$potential/$system"
	if [[ "$system" == "graphite.AA.6x6x4" ]]; then
            site="AA"
        else
            site="AB1" # only the most stable site
        fi
        for path in ${Na_loc}/${potential}/${system}/strain.c.*/${site}; do
            strain_dir="$(echo $path | sed -E 's/.+(strain[^/]+).+/\1/')"
            strain="$(echo $path | sed -E 's/.+strain\.c\.([0-9]\.[0-9]+).+/\1/')"
            site_source="$path"
            prototype_source="$prototype/$potential/$system/$strain_dir"
            dest="$root/$potential/$system/$strain_dir"
            # We use odd number of images: our structure is symmetric
            # and it is likely that path barrier is in the middle
            # We should better have point there to get the barrier
            # energy more accurately
            # Also, use 5ans cutoff (scale with strain)
            cutoff="$(echo 5 '*' \($strain + 1\) | bc)"
	    imdg -v derive "$prototype_source" --output="$dest" neb_diffusion --diffusion_points "$site_source" --nimages 5 --cutoff $cutoff --fix_dist=8.0 --frac_tol=0.6
        done
    done	
done

