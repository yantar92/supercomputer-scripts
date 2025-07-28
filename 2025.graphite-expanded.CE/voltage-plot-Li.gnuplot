#!/usr/bin/env gnuplot
set term pngcairo enhanced font ',12' enhanced size 960,720 fontscale 1.0 lw 1.0 dashlength 0.5
set output 'voltage.png'
set datafile missing "NaN"
set title "Voltage (" . system('pwd') . ")"
set xlabel "Relative concentration"
set ylabel "Voltage, V"
set key top right
set yrange [-5:1]
set xrange [-0.01:0.5]
OPT="every ::1 u 2:3 w steps"
OPTERR="every ::1 u 2:($3>$4?NaN:$3):4 w yerrorbars"
set arrow from 1/3.0, graph 0 to 1/3.0, graph 1 nohead lw 2 lc rgb'red'
set label at 1/3.0, graph 0 offset char 1, char 1 "MeC_{6}" textcolor rgb'red'
plot \
'AA/strain.c.0.00/voltage.out' @OPT ls 1 t'AA/strain=0%', \
'AA/strain.c.0.15/voltage.out' @OPT ls 2 t 'AA/strain=15%',\
'AA/strain.c.0.30.simplify.sublattice/voltage.out' @OPT ls 3 t 'AA/strain=30%'
# 'AA/strain.c.0.30/voltage.out' @OPTERR ls 3 not,\
# 'AA/strain.c.0.00/voltage.out' @OPTERR ls 1 not, \
# 'AA/strain.c.0.13/voltage.out' @OPTERR ls 2 not,\
# 'AB/strain.c.0.00.simplify.sublattice/voltage.out' @OPT ls 4 dt 4 t 'AB/strain=0%',\
# 'AB/strain.c.0.00.simplify.sublattice/voltage.out' @OPTERR ls 4 not,\
# 'AB/strain.c.0.13.simplify.sublattice/voltage.out' @OPT ls 5 dt 4 t 'AB/strain=15%',\
# 'AB/strain.c.0.13.simplify.sublattice/voltage.out' @OPTERR ls 5 not,\
# 'AB/strain.c.0.30.simplify.sublattice/voltage.out' @OPT ls 6 dt 4 t 'AB/strain=30%',\
# 'AB/strain.c.0.30.simplify.sublattice/voltage.out' @OPTERR ls 6 not
