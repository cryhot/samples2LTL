#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from rq import Queue, Worker, Connection
from redis import Redis
from random import seed
from random import random
import csv
import os
import glob
from pprint import pprint
import itertools
import argparse
from run_tests import subprocess_calls
from utils import datas

'''
******************For running multiple files using redis******************


Run the following commands to run experiments from a traces folder concurrently using multi-core processor

- Install redis servers using sudo apt-get install redis-server

-First run the queue-maker with the desired arguments (check --help for more arguments)

python queue_maker.py -tf <foldername> -o <outputfilename> -k <> -nw <numberworkers>


-Spawn the desired number of workers (default is 5) for running flie-PSL on different threads
-Write this command as many times as many workers you want

rq worker -b -q samples2LTL &

-




******************For Compiling the results******************

In the main-function in queue-maker: Comment out m.populate_queue() and uncomment m.compile_results()

Run queuemaker again, with the same arguments as in the first step, to compile the results

python queue_maker.py

'''

class multiprocess:

	def __init__(self, tracesFolderName, timeout, *, args=[], kwargs={}):

		self.tracesFolderName = tracesFolderName
		self.timeout = timeout
		self.args = args
		self.kwargs = kwargs
		self.flieTracesFileList = []
		for root, dirs, files in os.walk(self.tracesFolderName):
			for file in files:
				if file.endswith('.trace'):
					flie_file_name = str(os.path.join(root, file))
					self.flieTracesFileList.append(flie_file_name)
		if self.tracesFolderName.endswith('.trace'):
			self.flieTracesFileList.append(self.tracesFolderName)



	def populate_queue(self):
		redis_conn= Redis()
		q = Queue('samples2LTL', connection=redis_conn)
		q.empty()

		for args, kwargs in argproduct((self.flieTracesFileList, *self.args), self.kwargs):
			tracesFileName = args[0]
			id = (args, tuple(sorted(kwargs.items())))
			id = datas.microhash(id)
			job_id = f"{tracesFileName}.{id}"
			# output_filename = f"{job_id}-out.csv"
			if 1:
				# print(output_filename)
				q.enqueue(subprocess_calls,
					args=(
						# tracesFileName,
						*args,
					),
					kwargs=dict(
						# output_filename=output_filename,
						**kwargs,
					),
					job_timeout=self.timeout,
					job_id=job_id,
				)
			else:
				subprocess_calls(
					# tracesFileName,
					*args,
					# output_filename=output_filename,
					**kwargs,
				)

		print('Length of queue', len(q))



	def compile_results(self, results_file):

		#raise NotImplementedError("code require change")
		#work-around code

		with open(self.tracesFolderName+results_file+'.csv', 'w') as file1:
			writer = csv.writer(file1)
			csvInfo = [['File Name', 'Time', 'Formula Size', 'Output formula']]
			csvFileList = []

			#Reading all the csv files in the folder
			for root, dirs, files in os.walk(self.tracesFolderName):
				for file in files:
					if file.endswith('.csv'):
						csvFileList.append(str(os.path.join(root, file)))
			csvFileList.remove(self.tracesFolderName+results_file+'.csv')
			#Collating the results

			for csvFileName in csvFileList:
				with open(csvFileName, 'r') as file2:
					rows = csv.reader(file2)
					row_list = list(rows)
					tracesFileName = csvFileName.split('.')[0]+'.trace'

					csvrow = row_list[0]

				csvInfo.append(csvrow)

			writer.writerows(csvInfo)

		#for csvfile in csvFileList:
		#	os.remove(csvfile)


def str2nums(string):
	"""Returns a list of numbers from a string such as "1,5,10:20,100:200:10".
	Ranges are standard in python (start included, stop excluded).
	"""
	ans = []
	for sub in str(string).split(','):
		bounds = sub.split(":", 2)
		for i,n in enumerate(bounds):
			try:
				bounds[i] = int(n)
			except ValueError:
				bounds[i] = float(n)
		if len(bounds) == 1:
			ans.append(*bounds)
		else:
			ans.extend(numpy.arange(*bounds))
	return ans

def argproduct(args=[], kwargs={}):
	"""Like itertools.product but for arguments.
	:return: (args, kwargs) pairs generator
	"""
	argslist = list(args)
	kwi = len(argslist)
	keys, kwargslist = zip(*kwargs.items())
	argslist.extend(kwargslist)
	argslist = [
		tuple(arglist) if hasattr(arglist, '__iter__') and not isinstance(arglist, (str,bytes)) else (arglist,)
		for arglist in argslist
	]
	return (
		(args[:kwi], dict(zip(keys, args[kwi:])))
		for args in itertools.product(*argslist)
	)

def get_parser(parser=None):

	if parser is None:
		parser = argparse.ArgumentParser()

	if parser.epilog is None:
		parser.epilog = ""
	parser.epilog += """
		note: certain argument can take multiple value at the same time.
		Certain parameters can even accept ranges of values (start:stop[:step]).
		For example, you can specify:
		--min_score .5:.7:.025 --min_score .7,.8,.95
		If multiple parameters are multivalued, the cartesian product is made.
	"""

	group_multiproc = parser.add_argument_group('multiprocessing arguments')
	group_multiproc.add_argument('-c', '--compile',
		dest='compile',
		action='store_true',
		help="compile results (default: populate queue)",
	)
	group_multiproc.add_argument('-r', '--results_file',
		dest='results_file',
		default='compiled',
		help="file to store the compiled results",
	)


	group_multiproc.add_argument("-f", "--traces_folder",
	    dest='traces_folder',
	    default="../all_traces_maxsat/",
		help="trace file/folder to run",
	)
	group_multiproc.add_argument("-T", "--timeout", metavar="T",
	    dest='timeout', default=900,
	    type=int,
	    help="timeout in seconds",
	)
	group_multiproc.add_argument("--shutdown-timeout", metavar="T",
	    dest='shutdownTimeout', default=None,
	    type=int,
	    help="additionnal time given to the process to shut itself down before killing it (default: 2+timeout/10 seconds)",
	)
	fileformatstrings = list("{%s}" % (key,) for key in subprocess_calls.fileformatstrings)
	group_multiproc.add_argument("--output-folder-format", metavar="DIRNAME",
	    dest='output_dirname',
	    default="{tracesdir}",
		help=f"""Output folder (default is where the trace is).
			Can contain such formats: {', '.join(fileformatstrings)}.
		""",
	)
	group_multiproc.add_argument("--output-file-format", metavar="BASENAME",
	    dest='output_basename',
	    # default="{tracesname}.{method}{ext}",
	    default="{tracesname}.{method}-{argshash}.out{ext}",
		help=f"""
			Possible formats are {', '.join(fileformatstrings)}.
		""",
	)

	group_method = parser.add_mutually_exclusive_group(required=True)
	group_method.add_argument("--test",
	    dest='method',
	    choices=subprocess_calls.methods,
	)
	group_method.add_argument("--test_sat_method",
	    dest='method',
	    const='SAT', action='store_const',
		help='Ivan base algo',
	)
	group_method.add_argument("--test_maxsat_method",
	    dest='method',
	    const='MaxSAT', action='store_const',
		help='ATVA base algo',
	)
	group_method.add_argument("--test_sat_dt_method",
	    dest='method',
	    const='SAT-DT', action='store_const',
		help='Ivan base Decision tree,',
	)
	group_method.add_argument("--test_maxsat_dt_method",
	    dest='method',
	    const='MaxSAT-DT', action='store_const',
		help='ATVA Decision tree',
	)

	parser.add_argument("--misclassification", metavar="R",
	    dest="misclassification", default=0,
	    type=float,
	)

	group_sat = parser.add_argument_group('sat/maxsat method arguments')
	group_sat.add_argument("--start_depth", metavar="I",
	    dest='startDepth', default=1,
	    type=int,
	    help="formula start at size I",
	)
	group_sat.add_argument("--max_depth", metavar="I",
	    dest='maxDepth', default=float("inf"),
	    type=int,
	    help="search for formula of size < I",
	)
	group_sat.add_argument("--iteration_step", metavar="I",
	    dest='step', default=1,
	    type=int,
	    help="increment formula size by I at each iteration",
	)
	group_maxsat = group_sat
	group_maxsat.add_argument("--optimize_depth", metavar="I",
	    dest='optimizeDepth', #default=1 if 'MaxSAT' in args.method else float("inf"),
	    type=int, action='append',
	    help="use optimizer for formula size >= I",
	)
	group_maxsat.add_argument("--optimize", #metavar="SCORE",
	    dest='optimize', #default="count",
	    choices=['count', 'ratio'], action='append',
	    help="score to optimize",
	)
	group_maxsat.add_argument("--min_score", metavar="S",
	    dest='minScore', #default=0,
	    type=float, action='append',
	    help="formula should achieve a score > S",
	)
	# group_sat.add_argument("--max_num_formulas", metavar="N",
	#     dest='numFormulas', default=1,
	#     type=int,
	# )

	group_dt = parser.add_argument_group('dt method arguments')

	# parser.add_argument("--log", metavar="LVL",
	#     dest='loglevel', default="INFO",
	#     # choices="DEBUG, INFO, WARNING, ERROR, CRITICAL".split(", "),
	#     help="log level, usually in DEBUG, INFO, WARNING, ERROR, CRITICAL",
	# )

	return parser

def main():

	parser = get_parser()

	args,unknown = parser.parse_known_args()
	if args.shutdownTimeout is None: args.shutdownTimeout = int(2 + 0.1*args.timeout)

	if not args.optimizeDepth: args.optimizeDepth=[1 if 'MaxSAT' in args.method else float("inf")]
	if not args.optimize: args.optimize=['count']
	if not args.minScore: args.minScore=[0]

	# flattens lists
	for key in {'optimizeDepth', 'minScore'}:
		setattr(args, key, list(itertools.chain.from_iterable(str2nums(m) for m in getattr(args, key))))


	m = multiprocess(
		tracesFolderName=args.traces_folder,
		timeout=min(args.timeout+args.shutdownTimeout, 1e10),
		args=[
			args.method,
		],
		kwargs=dict(
			outputfile=os.path.join(args.output_dirname, args.output_basename),
			**{
				key: getattr(args, key)
				for key in subprocess_calls.keys[args.method]
				if hasattr(args, key)
			},
		),
	)

	if args.compile:
		m.compile_results(args.results_file)
	else:
		m.populate_queue()



if __name__ == '__main__':
    main()
