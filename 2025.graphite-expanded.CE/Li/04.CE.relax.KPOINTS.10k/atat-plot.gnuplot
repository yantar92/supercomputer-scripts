#!/usr/bin/env gnuplot
set term pngcairo enhanced font ',12' enhanced size 1920,960 fontscale 1.0 lw 1.0 dashlength 0.5
# set term qt font ',12' enhanced size 1920,960 lw 1.0 dashlength 0.5
set datafile missing "NaN"
set output "atat-summary.png"
global_title = system('pwd -P')
set multiplot layout 2,3 title global_title
set xlabel "concentration"
set ylabel "energy"
set key bottom left
set key maxrows 4
set title "Fitted Energies"
plot [0:1] \
'predstr.out' u 1:3 t "predicted" w p pt 2, \
'fit.out' u 1:3 t  "known str" w p pt 1, \
'gs.out' u 1:3 t "known gs" w linesp lt 3, \
'newgs.out' u 1:3 t "predicted gs" w p pt 4
set title "Calculated Energies"
plot [0:1] \
'fit.out' u 1:2 t  "known str" w p pt 5, \
'gs.out' u 1:2 t "known gs" w linesp lt 6 pt 6 ps 2, \
'encut-data.out' u 1:2 t "gs ENCUT = 600" w p pt 6 lc rgb'red' ps 2, \
'fixgs.out' u 1:2 t "fixed gs" w p pt 6 lc rgb'red' ps 2, \
'relax-data.out' u 1:2 t "relax gs" w p ps 2, \
'relax-data.out' u 1:3 t "perturb gs" w p ps 2
set title "Calculated and Fitted Energies"
plot [0:1] \
'fit.out' u 1:2 t  "calculated" w p pt 5, \
'fit.out' u 1:3 t  "fitted" w p pt 1 
set title "Residuals of the fit (same order as in fit.out)"
set xtics autofreq
set ylabel "energy"
set xlabel "line number in fit.out"
plot 'fit.out' u 4
CVE = system('tail -n1 maps.log')
set title "Fitted vs Calculated Energies " . '(' . CVE . ')'
set ylabel "predicted energy"
set xlabel "actual energy"
set nokey
plot \
'fit.out' u 2:3 w p pt 1,x
set xlabel "diameter"
set ylabel "energy"
set title "ECI vs cluster diameter"
set nokey
set xzeroaxis
set xtics ("pair" 0,"5" 5,"10" 10,"15" 15, "trip" 20,"5" 25,"10" 30,"15" 35, "quad" 40,"5" 45,"10" 50,"15" 55)
plot [-5:60] 'clusinfo.out' u (($1-2)*20.+$2):($4)
unset multiplot
