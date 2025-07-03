#!/usr/bin/env bash
# [[file:/home/yantar92/Org/notes.org::*Workflow v2 (new folder structure)][Workflow v2 (new folder structure):1]]
# 1. Create supercells from the relaxed structures for each potential
for potential in PBE+TS optB88-vdW; do
    for system in graphite.AA graphite.AB; do
	source="../01.graphite.relax.FIX_NONE/$potential/$system"
	[[ "$system" == "graphite.AA" ]] && size="6x6x4" || size="6x6x2"
        dest="$potential/$system.$size"
        mkdir -p "$dest/.source"
        imdg derive "$source" --output="$dest/.source" supercell $size
    done	
done

# 2. Create supercells with various interlayer distances; this also
# sets selective dynamics
root="$(pwd)"
for potential in PBE+TS optB88-vdW; do
    for system in graphite.AA graphite.AB; do
	[[ "$system" == "graphite.AA" ]] && size="6x6x4" || size="6x6x2"
        cd "$potential/$system.$size"
        imdg derive ".source" --output-prefix="" strain --cmin=100 --cmax=130 --csteps=10 --selective-dynamics True True False
        ~/data/walk-dirs-level 1 'mkdir -p .source'
        ~/data/walk-dirs-level 1 'mv -t .source *'
        cd "$root"
    done	
done

# 3. Generate all possible inserts of Na
root="$(pwd)"
for potential in PBE+TS optB88-vdW; do
    for system in graphite.AA graphite.AB; do
	[[ "$system" == "graphite.AA" ]] && size="6x6x4" || size="6x6x2"
        cd "$potential/$system.$size"
        ~/data/walk-dirs-level 1 imdg derive ".source" --output-prefix="" ins Na --step=0.1 --threshold=0.5
        ~/data/walk-dirs-level 2 'mkdir -p .source'
        ~/data/walk-dirs-level 2 'mv -t .source *'
        cd "$root"
    done	
done

# 4. Disable writing WAVECAR and CHGCAR - the copied over INCARs are
# from older versions of the scripts that do not yet disable those.
# Also, set ENCUT=500
root="$(pwd)"
for potential in PBE+TS optB88-vdW; do
    for system in graphite.AA graphite.AB; do
	[[ "$system" == "graphite.AA" ]] && size="6x6x4" || size="6x6x2"
        cd "$potential/$system.$size"
	~/data/walk-dirs-level 2 imdg derive ".source" --output=".source2" incar NCORE:16 LWAVE:False LCHARG:False ENCUT:500.0
        cd "$root"
    done	
done

# 5. Generate position relaxation
root="$(pwd)"
for potential in PBE+TS optB88-vdW; do
    for system in graphite.AA graphite.AB; do
	[[ "$system" == "graphite.AA" ]] && size="6x6x4" || size="6x6x2"
        cd "$potential/$system.$size"
	~/data/walk-dirs-level 2 imdg derive ".source2" --output="./" relax RELAX_POS
        cd "$root"
    done	
done

# 6. Run relaxation
# root="$(pwd)"
# for potential in PBE+TS optB88-vdW; do
#     for system in graphite.AA graphite.AB; do
# 	[[ "$system" == "graphite.AA" ]] && size="6x6x4" || size="6x6x2"
#         cd "$potential/$system.$size"
# 	~/data/walk-dirs-level 2 gorun-helios
#         cd "$root"
#     done	
# done
# Workflow v2 (new folder structure):1 ends here
