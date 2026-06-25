#!/usr/bin/env bash
SOURCE_PATH="$1"
[[ -d "$1" ]] || (echo "Should pass dir to copy as argument"; exit 1)
TARGET_PATH="$(pwd)"
cd "$SOURCE_PATH"
cp lat.in "$TARGET_PATH"
imdg derive . --output="${TARGET_PATH}" functional optB88-vdW
imdg derive $TARGET_PATH --output="${TARGET_PATH}" incar ENCUT:550 EDIFFG:-0.01 ALGO:All SYMPREC:1E-9 NELMIN:6
# Maybe manually adjust ISIF=3 for d-spacing relaxation
# only copy immediate structures
# for perturbation and other functionals, re-generate
# prioritize str.out.old original structures
find . -maxdepth 2 -iname "str.out.old" | while read x; do
    mkdir -p "${TARGET_PATH}/$(dirname $x)"
    cp $x "${TARGET_PATH}/$(dirname $x)/str.out"
done
# if no str.out.old, use str.out
find . -maxdepth 2 -iname "str.out" | while read x; do
    [[ -f "${TARGET_PATH}/$(dirname $x)" ]] && continue
    mkdir -p "${TARGET_PATH}/$(dirname $x)"
    cp $x "${TARGET_PATH}/$(dirname $x)/str.out"
done
cd -

