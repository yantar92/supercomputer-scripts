#!/usr/bin/env bash
find . -maxdepth 3 -iname "near_hull.txt" | while read parent; do
    (cd $(dirname $parent);
     cat near_hull.txt | sort | while read x; do
	 x=$(echo $x | sed -E 's|[^/]+/||')
	 [ ! -d "$x" ] && echo "Skipping $x" && continue;
	 for d in optB86b-vdW PBE+D2 vdW-DF vdW-DF2; do
	     (
		 cd $d/$x;
		 echo $(dirname $parent)/$d/$x;
		 if [ ! -f energy ]; then
		     [ -f error ] && rm error*;
		     ../../../../run_all.py --max_jobs=450;
		     sleep 1;
                 fi
	     );
	 done
     done
    )
done
