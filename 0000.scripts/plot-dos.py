#!/usr/bin/env python3
# [[file:/home/yantar92/Org/notes.org::*DOS plot][DOS plot:1]]
import argparse
import pymatgen.cli.pmg_plot as pmgp

args = argparse.Namespace()
args.dos_file = 'vasprun.xml'
args.site = None
args.element = None
args.orbital = None
dos_plot = pmgp.get_dos_plot(args)
dos_plot.figure.savefig('dos.png')
# DOS plot:1 ends here
