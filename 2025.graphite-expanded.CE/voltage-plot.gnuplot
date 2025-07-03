#!/usr/bin/env gnuplot
set term pngcairo enhanced font ',12' enhanced size 960,720 fontscale 1.0 lw 1.0 dashlength 0.5
set output 'voltage.png'
set datafile missing "NaN"
set title "Voltage (" . system('pwd') . ")"
set xlabel "Relative concentration"
set ylabel "Voltage, V"
set key bottom left
OPT="every ::1 u 2:3 w steps"
set xrange [-0.1:1.1]
set arrow from 1/3.0, graph 0 to 1/3.0, graph 1 nohead lw 2 lc rgb'red'
set label at 1/3.0, graph 0 offset char 1, char 1 "MeC_{6}" textcolor rgb'red'
plot \
'AA/strain.c.0.00/voltage.out' @OPT t'AA/strain=0%', \
'AA/strain.c.0.15/voltage.out' @OPT t 'AA/strain=15%',\
'AA/strain.c.0.30.simplify.sublattice/voltage.out' @OPT t 'AA/strain=30%',\
'AB/strain.c.0.00.simplify.sublattice/voltage.out' @OPT dt 4 t 'AB/strain=0%',\
'AB/strain.c.0.15.simplify.sublattice/voltage.out' @OPT dt 4 t 'AB/strain=15%',\
'AB/strain.c.0.30.simplify.sublattice/voltage.out' @OPT dt 4 t 'AB/strain=30%'
