#!/bin/sh
# -n num msg  -z seq num limit   -d avg. time between   -l loss -c corruption -s random seed -v trace
python3 rdtsim.py -n 1000 -z 2 -d 10 -l 0.0 -c 0.0 -s 3838383838 -v 1 > out.txt
bat out.txt
