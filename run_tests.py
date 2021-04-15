import time
import subprocess
import os
import csv
import shutil
import subprocess
import argparse
from utils.Traces import Trace, ExperimentTraces
from solverRuns import run_solver, run_dt_solver



#function for invoking samples2LTL: Ivan's tool
def subprocess_calls(
	traces_filename,
	method = 'SAT',
	misclassification=0.05
):

	# For outputing to csv file
	allTraces = ExperimentTraces()
	allTraces.readTracesFromFile(traces_filename)
	flie_formula, flie_time = run_solver(finalDepth=10, traces=allTraces)
	
	if method=='SAT':

		csvname = traces_filename.rstrip('.trace')+'-'+str(method)+'.csv'
		with open(csvname, 'w') as csvfile:
				writer = csv.writer(csvfile)
				if flie_formula!=[]:
					writer.writerow([traces_filename, str(round(flie_time, 2)), str(flie_formula[0].getNumberOfSubformulas()) , flie_formula[0].prettyPrint()])

	if method=='DT':
		pass

def main():
	subprocess_calls('0000.trace')


if __name__ == "__main__":
	main()




