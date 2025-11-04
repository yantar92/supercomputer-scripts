#!/usr/bin/env bash

get_n_jobs () {
    squeue -u $USER -o %Z | tail -n +2 | wc -l;
}

[ -z "$1" ] && max_jobs="100" || max_jobs="$1"
echo "Limiting max jobs to $max_jobs"
find . -iname "gorun_ready" | while read x; do
    [ "$(get_n_jobs)" -ge "$max_jobs" ] && echo "Waiting for submitted jobs to finish"
    while [ "$(get_n_jobs)" -ge "$max_jobs" ]; do
        sleep 5
    done
    (cd $(dirname $x);
     echo $x
     sbatch sub && rm gorun_ready)
done
