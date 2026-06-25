#!/usr/bin/env bash
find . -maxdepth 3 -iname "lat.in" | while read parent; do
    (
        cd $(dirname $parent);
	for d in optB86b-vdW PBE+D2 vdW-DF vdW-DF2; do
            [ ! -d "$d" ] && continue
	    (
                cd "$d"
                find . -mindepth 1 -maxdepth 1 -type d | while read x; do
		    x="$(basename $x)";
                    cat ../near_hull.txt | grep $x >/dev/null || (echo "$d/$x not near null"; touch $x/error; touch $x/error_highen);
		done
	    );
	done
    )	
done

find . -maxdepth 3 -iname "near_hull.txt" | while read parent; do
    (cd $(dirname $parent);
     cat near_hull.txt | sort | while read x; do
	 x=$(echo $x | sed -E 's|[^/]+/||')
	 [ ! -d "$x" ] && echo "Skipping $x" && continue;
	 for d in optB86b-vdW PBE+D2 vdW-DF vdW-DF2; do
             [ ! -d "$d/$x" ] && continue
	     (
		 cd $d/$x;
		 echo $(dirname $parent)/$d/$x;
		 if [ ! -f energy ]; then
		     [ -f error ] && rm error*;
		     ../../../../run_all.py --max_jobs=450 --mark;
		     sleep 1;
                 fi
	     );
	 done
     done
    )
done
