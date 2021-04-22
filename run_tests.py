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
	record = datas.Data()
	record['traces'] = datas.json_traces_file(
		filename=traces_filename,
	)

	if 'MaxSAT' in method: solver_args.setdefault('optimizeDepth', 1)
	if method=="SAT" and 'optimizeDepth' in solver_args and solver_args['optimizeDepth'] < solver_args['maxDepth']:
		method="MaxSAT"

	record['algo'] = datas.json_algo(
	    name=method,
	    args={
			key: arg
			for key,arg in sorted(solver_args.items())
			if key in subprocess_calls.keys[method]
		},
	)

	recordoutputfile = subprocess_calls._format_filename(outputfile, record, ext=".json")
	csvoutputfile = subprocess_calls._format_filename(outputfile, record, ext=".csv")

	with open(recordoutputfile, 'w') as f:
		json.dump(record, f, indent="\t")

	os.makedirs(os.path.realpath(os.path.dirname(recordoutputfile)), exist_ok=True)

	try:
		if method in {'SAT', 'MaxSAT'}:

			row = [traces_filename, solver_args.get('timeout'), None, None]
			with open(csvoutputfile, 'w') as csvfile:
				writer = csv.writer(csvfile)
				writer.writerow(row)

			formulas, timePassed = run_solver(
				traces=traces,
				maxNumModels=1,
				# startDepth=args.startDepth, maxDepth=args.maxDepth, step=args.iterationStep,
				# optimizeDepth=args.optimizeDepth,
				# optimize=args.optimize, minScore=args.minScore,
            	# timeout=args.timeout,
				**solver_args,
			)
			record['run'] = datas.Data(
			    time=timePassed,
			    success=len(formulas)>0,
			)
			if record['run']['success']:
			    formula = formulas[0]
			    record['result'] = datas.Data(
			        formula=formula.prettyPrint(),
			        nSub=formula.getNumberOfSubformulas(),
					depth=formula.getDepth(),
					misclassification=traces.get_misclassification(formula),
			    )
			    row = [traces_filename, timePassed, formula.getNumberOfSubformulas() , formula.prettyPrint()]

			with open(csvoutputfile, 'w') as csvfile:
				writer = csv.writer(csvfile)
				writer.writerow(row)


		elif method == 'MaxSAT-DT':

			formulaTree, timePassed = run_rec_dt(
				traces=traces,
				# startDepth=args.startDepth, maxDepth=args.maxDepth, step=args.iterationStep,
				# optimizeDepth=args.optimizeDepth,
				# optimize=args.optimize, minScore=args.minScore,
				# misclassification=args.misclassification,
				# timeout=args.timeout,
				**solver_args,
			)
			record['result'] = datas.Data(
			    decisionTree=formulaTree.prettyPrint(),
			    sizeDT=formulaTree.getSize(),
			    depthDT=formulaTree.getDepth(),
			)
			trimedFormulaTree = formulaTree.trimPseudoNodes()
			record['run'] = datas.Data(
			    time=timePassed,
			    success=trimedFormulaTree is formulaTree,
			)
			if trimedFormulaTree is not None:
				flatFormula = trimedFormulaTree.flattenToFormula()
				record['result'].update(
				    formula=flatFormula.prettyPrint(),
					nSub=flatFormula.getNumberOfSubformulas(),
					depth=flatFormula.getDepth(),
					misclassification=traces.get_misclassification(flatFormula),
				)

		elif method == 'SAT-DT':

			try:
				record_result = {}
				timePassed, numAtoms, numPrimitives = run_dt_solver(
		            traces=traces,
					txtFile=subprocess_calls._format_filename(outputfile, record, ext=".txt"),
					**solver_args,
					record_result=record_result,
		        )

				record['result'] = datas.Data(
				    numAtoms=numAtoms,
				    numPrimitives=numPrimitives,
				)
				formulaTree = record_result.pop('formulaTree')
				if formulaTree is not None:
					record['result'].update(
					    decisionTree=formulaTree.prettyPrint(),
					    sizeDT=formulaTree.getSize(),
					    depthDT=formulaTree.getDepth(),
					)
					trimedFormulaTree = formulaTree.trimPseudoNodes()
					record['run'] = datas.Data(
					    time=timePassed,
					    success=trimedFormulaTree is formulaTree,
					)
					if trimedFormulaTree is not None:
						flatFormula = trimedFormulaTree.flattenToFormula()
						record['result'].update(
						    formula=flatFormula.prettyPrint(),
							nSub=flatFormula.getNumberOfSubformulas(),
							depth=flatFormula.getDepth(),
							misclassification=traces.get_misclassification(flatFormula),
						)
			except Exception as err:
				record['run'] = dict(
				    time=solver_args.get('timeout'),
				    success=False,
				)
				raise err


		else:
			raise NotImplementedError()

	finally:

		# pprint(record)
		# df = pandas.DataFrame([datas.json_flatten(record)]*5)
		# pprint(df)

		with open(recordoutputfile, 'w') as f:
			json.dump(record, f, indent="\t")

subprocess_calls.methods = methods = {'SAT','MaxSAT','SAT-DT','MaxSAT-DT'}
subprocess_calls.keys = keys = dict()
keys['*'] = {'timeout'}
keys['SAT'] = keys['*']|{'startDepth','maxDepth','step'}
keys['MaxSAT'] = keys['SAT']|{'optimizeDepth','optimize','minScore'}
keys['MaxSAT-DT'] = keys['MaxSAT']|{'misclassification'}
keys['SAT-DT'] = keys['*']|{'misclassification'}
# keys['?']=functools.reduce(operator.or_, keys.values(), set())
subprocess_calls.fileformatstrings = {
	'method':     (lambda rec, d: rec['algo']['name']),
	'argshash':   (lambda rec, d: datas.microhash(tuple(sorted(datas.json_flatten(rec['algo']).items())))),
	'ext':        (lambda rec, d: d['ext']),
	'tracesdir':  (lambda rec, d: os.path.realpath(os.path.dirname(rec["traces"]["filename"]))),
	'tracesname': (lambda rec, d: os.path.splitext(os.path.basename(rec["traces"]["filename"]))[0]),
	'tracesext':  (lambda rec, d: os.path.splitext(os.path.basename(rec["traces"]["filename"]))[1]),
}
for key in functools.reduce(operator.or_, subprocess_calls.keys.values(), set()):
	subprocess_calls.fileformatstrings[f'{key}'] = (lambda rec, d: rec['algo']['args'].get(key))
subprocess_calls._format_filename = lambda outputfile, record, **d: outputfile.format(**{
	key:getval(record, d) for key,getval in subprocess_calls.fileformatstrings.items()
})

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
