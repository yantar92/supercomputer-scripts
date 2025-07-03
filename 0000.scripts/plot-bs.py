#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*Inputs][Inputs:4]]
from pymatgen.io.vasp.outputs import Vasprun
from pymatgen.electronic_structure.plotter import BSPlotter
from matplotlib import pyplot as plt

vasp_output = Vasprun('vasprun.xml')
bandstr = vasp_output.get_band_structure(line_mode=True)

bands_plot = BSPlotter(bandstr).get_plot()
bands_plot.tick_params(axis="x", labelsize="small",labelrotation=45)
bands_plot.tick_params(axis="y", labelsize="small")
bands_plot.figure.savefig('band.png')
# Inputs:4 ends here
