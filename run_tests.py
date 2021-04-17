#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import subprocess
import os
import csv
import json
from pprint import pprint
import shutil
import subprocess
import argparse
import functools, itertools, operator
from utils.Traces import Trace, ExperimentTraces, parseExperimentTraces
from solverRuns import run_solver, run_rec_dt, run_dt_solver

from utils import datas

def subprocess_calls(
	traces_filename,
	method='SAT',
	outputfile=os.path.join("{tracesdir}", "{tracesname}{ext}"),
	**solver_args,
):
	traces = parseExperimentTraces(traces_filename)

	# keep record
	record = dict()
	record['traces'] = datas.json_traces_file(
		filename=traces_filename,
	)

	try:
		if method in {'SAT', 'MaxSAT'}:

			if method == 'MaxSAT': solver_args.setdefault('optimizeDepth', 1)

			method="SAT"
			if 'optimizeDepth' in solver_args and solver_args['optimizeDepth'] < solver_args['maxDepth']:
			    method="MaxSAT"
			else:
			    for a in {'optimizeDepth','optimize','minScore'}:
			        solver_args.pop(a, None)
			record['algo'] = datas.json_algo(
			    name=method,
			    args={
					key: arg
					for key,arg in sorted(solver_args.items())
					if key in subprocess_calls.keys[method]
				},
			)

			formulas, timePassed = run_solver(
				traces=traces,
				maxNumModels=1,
				# startDepth=args.startDepth, maxDepth=args.maxDepth, step=args.iterationStep,
				# optimizeDepth=args.optimizeDepth,
				# optimize=args.optimize, minScore=args.minScore,
            	# timeout=args.timeout,
				**solver_args,
			)
			record['run'] = dict(
			    time=timePassed,
			    success=len(formulas)>0,
			)
			if record['run']['success']:
			    formula = formulas[0]
			    record['result'] = dict(
			        formula=formula.prettyPrint(),
			        nSub=formula.getNumberOfSubformulas(),
					depth=formula.getDepth(),
					misclassification=1-traces.get_score(formula, score='count'),
			    )

		elif method == 'MaxSAT-DT':

			solver_args.setdefault('optimizeDepth', 1)

			record['algo'] = datas.json_algo(
			    name=method,
			    args={
					key: arg
					for key,arg in sorted(solver_args.items())
					if key in subprocess_calls.keys[method]
				},
			)

			formulaTree, timePassed = run_rec_dt(
				traces=traces,
				# startDepth=args.startDepth, maxDepth=args.maxDepth, step=args.iterationStep,
				# optimizeDepth=args.optimizeDepth,
				# optimize=args.optimize, minScore=args.minScore,
				# misclassification=args.misclassification,
				# timeout=args.timeout,
				**solver_args,
			)
			trimedFormulaTree = formulaTree.trimPseudoNodes()
			flatFormula = trimedFormulaTree.flattenToFormula()
			record['run'] = dict(
			    time=timePassed,
			    success=trimedFormulaTree is formulaTree,
			)
			record['result'] = dict(
			    decisionTree=formulaTree.prettyPrint(),
			    sizeDT=trimedFormulaTree.getSize(),
			    depthDT=trimedFormulaTree.getDepth(),
			    formula=flatFormula.prettyPrint(),
				nSub=flatFormula.getNumberOfSubformulas(),
				depth=flatFormula.getDepth(),
				misclassification=1-traces.get_score(trimedFormulaTree, score='count'),
			)

		elif method == 'SAT-DT':
			raise NotImplementedError()

		else:
			raise NotImplementedError()

	finally:

		# pprint(record)
		# df = pandas.DataFrame([datas.json_flatten(record)]*5)
		# pprint(df)

		outputfile = outputfile.format(**{key:getval(record) for key,getval in subprocess_calls.fileformatstrings.items()})
		os.makedirs(os.path.realpath(os.path.dirname(traces_filename)), exist_ok=True)
		with open(outputfile, 'w') as f:
			json.dump(record, f)

subprocess_calls.methods = methods = {'SAT','MaxSAT','SAT-DT','MaxSAT-DT'}
subprocess_calls.keys = keys = dict()
keys['*'] = {'timeout'}
keys['SAT'] = keys['*']|{'startDepth','maxDepth','step'}
keys['MaxSAT'] = keys['SAT']|{'optimizeDepth','optimize','minScore'}
keys['MaxSAT-DT'] = keys['MaxSAT']|{'misclassification'}
keys['SAT-DT'] = {'misclassification'}
# keys['?']=functools.reduce(operator.or_, keys.values(), set())
subprocess_calls.fileformatstrings = {
	'method':     (lambda record: record['algo']['name']),
	'argshash':   (lambda record: datas.microhash(tuple(sorted(datas.json_flatten(record['algo']).items())))),
	'ext':        (lambda record: '.json'),
	'tracesdir':  (lambda record: os.path.realpath(os.path.dirname(record["traces"]["filename"]))),
	'tracesname': (lambda record: os.path.splitext(os.path.basename(record["traces"]["filename"]))[0]),
	'tracesext':  (lambda record: os.path.splitext(os.path.basename(record["traces"]["filename"]))[1]),
}
for key in functools.reduce(operator.or_, subprocess_calls.keys.values(), set()):
	subprocess_calls.fileformatstrings[f'{key}'] = (lambda record: record['algo']['args'].get(key))

'''
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
'''

def main():
	subprocess_calls(
		"traces/dummy.trace",
		# startDepth=2,
	)


if __name__ == "__main__":
	main()
