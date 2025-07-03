#!/bin/bash

[[ ! -d gorun1 ]] && echo "No gorun1 found" && exit 1
[[ -d gorun1.SCF ]] && echo "gorun1.SCF already present" && exit 1

imdg derive gorun1 scf || exit 1
cd gorun1.SCF && gorun 1 1:00:00
cd ..
