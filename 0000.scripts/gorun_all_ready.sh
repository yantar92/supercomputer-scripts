#!/usr/bin/env bash
find . -iname "gorun_ready" | while read x; do
    (cd $(dirname $x);
     echo $x
     sbatch sub && rm gorun_ready)
done
