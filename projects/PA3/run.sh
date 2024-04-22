# test 205.3
#python3 rdtsim.py -n 10000 -d 14 -z 8 -l 0.1 -c 0.1 -s 595959595959 -v 0

# test 205.2
#python3 rdtsim.py -n 10000 -d 12 -z 8 -l 0.08 -c 0.08 -s 4734747747 -v 0

# test 205.1
#python3 rdtsim.py -n 10000 -d 6 -z 8 -l 0.01 -c 0.01 -s 4734747747 -v 0

# test 202.1
#python3 rdtsim.py -n 1000 -d 10 -z 8 -l 0.0 -c 0.0 -s 3838383838 -v 0

# test 203.2
#python3 rdtsim.py -n 1000 -d 7 -z 8 -l 0.05 -c 0.0 -s 57575757578 -v 0

# test 204.3
#python3 rdtsim.py -n 1000 -d 8 -z 8 -l 0.0 -c 0.08 -s 848484848484 -v 0

# test 204.4
#python3 rdtsim.py -n 1000 -d 9 -z 8 -l 0.0 -c 0.1 -s 2626262626262 -v 0

# test 102.3
#python3 rdtsim.py -n 1000 -d 100 -z 8 -l 0.0 -c 0.0 -s 7567575757 -v 1

# Output
#python3 rdtsim.py -n 25 -l 0.05 -c 0.05 -v 2



# simulation

echo "ONE ---------------------------------------"
python3 rdtsim.py -n 10000 -d 10 -z 8 -l 0.0 -c 0.0 -v 0

echo "TWO ---------------------------------------"
# test 203.2
python3 rdtsim.py -n 10000 -d 100 -z 8 -l 0.05 -c 0.0 -v 0

echo "THREE ---------------------------------------"
# test 204.3
python3 rdtsim.py -n 10000 -d 30 -z 8 -l 0.0 -c 0.08 -v 0

echo "FOUR ---------------------------------------"
# test 204.4
python3 rdtsim.py -n 10000 -d 13 -z 20 -l 0.1 -c 0.1 -v 0
