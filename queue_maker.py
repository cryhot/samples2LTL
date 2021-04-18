#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from random import seed
from random import random
import numpy
import csv
import sys
import os
import glob
from pprint import pprint
import itertools
import functools
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



	def populate_queue(self, queue_handling="ENQUEUE"):
		"""
			:param queue_handling: "ENQUEUE" | "RUN" | "DRY"
		"""
		if queue_handling=="ENQUEUE":
			from rq import Queue, Worker, Connection
			from redis import Redis
			redis_conn= Redis()
			q = Queue('samples2LTL', connection=redis_conn)
			q.empty()

		for args, kwargs in argproduct((self.flieTracesFileList, *self.args), self.kwargs):
			tracesFileName = args[0]
			id = (args, tuple(sorted(kwargs.items())))
			id = datas.microhash(id)
			job_id = f"{tracesFileName}.{id}"
			# output_filename = f"{job_id}-out.csv"

			args=(
				# tracesFileName,
				*args,
			)
			kwargs=dict(
				# output_filename=output_filename,
				**kwargs,
			)
			if queue_handling=="ENQUEUE":
				# print(output_filename)
				q.enqueue(subprocess_calls,
					args=args, kwargs=kwargs,
					job_timeout=self.timeout,
					job_id=job_id,
				)
			elif queue_handling=="RUN":
				subprocess_calls(*args, **kwargs)
			else:
				kwargs.pop('outputfile', None)
				args = [
					*(f"{arg!r}" for arg in args),
					*(f"{key}={arg!r}" for key, arg in kwargs.items()),
				]
				print(f"subprocess_calls({', '.join(args)})")

		if queue_handling=="ENQUEUE":
			print('Length of queue', len(q))



def compile_results(tracesFolderName, results_file):

	#raise NotImplementedError("code require change")
	#work-around code

	results_file = os.path.join(tracesFolderName, results_file+'.csv')

	with open(results_file, 'w') as file1:
		writer = csv.writer(file1)
		csvInfo = [['File Name', 'Time', 'Formula Size', 'Output formula']]
		csvFileList = []

		#Reading all the csv files in the folder
		for root, dirs, files in os.walk(tracesFolderName):
			for file in files:
				if file.endswith('.csv'):
					csvFileList.append(str(os.path.join(root, file)))
		csvFileList.remove(results_file)
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

def parser_factory(name=None, *,
	aliases=(), help=None,
	override_args=False,
	**parser_args,
):
	""" Decorate a function that fill a parser with arguments.
	The decorated function will create it's own parser if necessary, and be able to handle subparsers.
		:param name, aliases, help: default used if this is a subparser.
			These can be overridden when the decorated function is called.
		:param override_args: if set while an existent parser is given, override specified parser configs
			amongst prog, usage, description, epilog (uses help instead of description if not specified)
		:returns: decorator
	"""
	if not 'description' in parser_args and help is not None:
		parser_args['description'] = help
	def decorator(func):
		@functools.wraps(func)
		def wrapper(parser=None, *args,
			name=name, aliases=aliases, help=help,
			override_args=override_args,
			**kwargs,
		):
			if parser is None:
				parser = argparse.ArgumentParser(
					**parser_args,
				)
			elif isinstance(parser, argparse._SubParsersAction):
				if name is None:
					msg = "Missing required argument when instanciating a subparser: 'name'"
					raise TypeError(msg)
				parser = parser.add_parser(name,
					aliases=aliases, help=help,
					**parser_args,
				)
			elif override_args:
				for attr in {'prog','usage','description','epilog'}:
					if not attr in parser_args: continue
					setattr(parser, attr, parser_args[attr])
			return func(parser, *args, **kwargs)
		return wrapper
	return decorator



@parser_factory("enqueue",
	help="run a batch of simulations",
	epilog="""
		note: certain argument can take multiple value at the same time.
		Certain parameters can even accept ranges of values (start:stop[:step]).
		For example, you can specify:
		--min_score .5:.7:.025 --min_score .7,.8,.95
		If multiple parameters are multivalued, the cartesian product is made.
	""",
	)
def createBatchParser(parser):
	parser.set_defaults(_handler=main_enqueue)

	group_multiproc = parser.add_argument_group(
		title='multiprocessing arguments'
	)
	group_multiproc.add_argument("-f", "--traces_folder",
	    dest='traces_folder',
	    default="../all_traces/",
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
	group_multiproc.add_argument("--enqueue",
	    dest='queue_handling', default="QUEUE",
	    const="QUEUE", action='store_const',
		help="Enqueue to Redis (default).",
	)
	group_multiproc.add_argument("--dry-run",
	    dest='queue_handling', #default="QUEUE",
	    const="DRY", action='store_const',
		help="Just print commands.",
	)
	group_multiproc.add_argument("--run-in-place",
	    dest='queue_handling', #default="QUEUE",
	    const="RUN", action='store_const',
		help="Run directly, without multiprocessing.",
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

	group_sat = parser.add_argument_group(
		title='sat/maxsat method arguments'
	)
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
	    action='append', #TODO: special action
	    help="use optimizer for formula size >= I",
	)
	group_maxsat.add_argument("--optimize", #metavar="SCORE",
	    dest='optimize', #default="count",
	    choices=['count', 'ratio'], action='append',
	    help="score to optimize",
	)
	group_maxsat.add_argument("--min_score", metavar="S",
	    dest='minScore', #default=0,
	    action='append', #TODO: special action
	    help="formula should achieve a score > S",
	)
	# group_sat.add_argument("--max_num_formulas", metavar="N",
	#     dest='numFormulas', default=1,
	#     type=int,
	# )

	group_dt = parser.add_argument_group(
		title='dt method arguments'
	)

	# parser.add_argument("--log", metavar="LVL",
	#     dest='loglevel', default="INFO",
	#     # choices="DEBUG, INFO, WARNING, ERROR, CRITICAL".split(", "),
	#     help="log level, usually in DEBUG, INFO, WARNING, ERROR, CRITICAL",
	# )

	return parser

	return parser

def main_enqueue(args):

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
				for key in vars(args)
				if key in subprocess_calls.keys[args.method]
			},
		),
	)

	m.populate_queue(args.queue_handling)



@parser_factory("compile",
	help="compile simulation results from csv",
	)
def createCompileCsvParser(parser):
	parser.set_defaults(_handler=main_compile_csv)

	parser.add_argument("-f", "--traces_folder",
	    dest='traces_folder',
	    default="../all_traces/",
		help="folder where the traces results to compile are.",
	)
	parser.add_argument('-r', '-o', '--results_file',
		dest='results_file',
		default='compiled',
		help="file to store the compiled results",
	)

def main_compile_csv(args):
	compile_results(args.traces_folder, args.results_file)



@parser_factory()
def createMainParser(parser):
	parser.set_defaults(_handler=lambda args: parser.print_help(sys.stderr))

	subparsers_command = parser.add_subparsers(metavar="COMMAND",
	    title="commands",
	    # required=True, # not working
		help="action to execute",
	)
	createBatchParser(subparsers_command)
	createCompileCsvParser(subparsers_command)

	return parser

def main():
	parser = createMainParser()
	args,unknown = parser.parse_known_args()
	args._handler(args)

if __name__ == '__main__':
    main()
