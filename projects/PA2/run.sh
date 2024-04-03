#!/bin/sh
# -n num msg  -z seq num limit   -d avg. time between   -l loss -c corruption -s random seed -v trace
echo "first run\n" > out.txt
python3 rdtsim.py -n 1000 -z 2 -d 100 -l 0.1 -c 0.0 -v 0 >> out.txt
echo "sec run\n" >> out.txt
python3 rdtsim.py -n 1000 -z 2 -d 100 -l 0.0 -c 0.1 -v 0 >> out.txt
echo "thir run\n" >> out.txt
python3 rdtsim.py -n 1000 -z 2 -d 100 -l 0.05 -c 0.1 -v 0 >> out.txt
echo "four run\n" >> out.txt
python3 rdtsim.py -n 1000 -z 2 -d 100 -l 0.1 -c 0.05 -v 0 >> out.txt
