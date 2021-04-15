from rq import Queue, Worker, Connection
from redis import Redis
from random import seed
from random import random
import csv
import os
import glob
import argparse
from run_tests import subprocess_calls

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

	def __init__(self, tracesFolderName, method, timeOut):
		
		self.tracesFolderName = tracesFolderName
		self.timeOut = timeOut
		self.method = method
		self.flieTracesFileList = []
		for root, dirs, files in os.walk(self.tracesFolderName):
			for file in files:
				if file.endswith('.trace'):
					flie_file_name = str(os.path.join(root, file))
					self.flieTracesFileList.append(flie_file_name)

		

	def populate_queue(self):
		redis_conn= Redis()
		q = Queue('samples2LTL', connection=redis_conn)
		q.empty()
		
		for flieFile in self.flieTracesFileList:

			q.enqueue(subprocess_calls, args=(flieFile,self.method \
												),\
						job_=self.timeOut, job_id=flieFile)


		print('Length of queue', len(q))

	
	def compile_results(self):

		with open(self.tracesFolderName+'compiled.csv', 'w') as file1:
			writer = csv.writer(file1)
			csvInfo = [['File Name', 'Flie Time', 'Flie Formula Size', 'Flie Output formula']]
			csvFileList = []

			#Reading all the csv files in the folder
			for root, dirs, files in os.walk(self.tracesFolderName):
				for file in files:
					if file.endswith('.csv'):
						csvFileList.append(str(os.path.join(root, file)))
									
			csvFileList.remove(self.tracesFolderName+'compiled.csv')
			
			#Collating the results

			for csvFileName in csvFileList:
				with open(csvFileName, 'r') as file2:
					rows = csv.reader(file2)
					row_list = list(rows)
					tracesFileName = csvFileName.split('output')[0]

					if row_list == []:
						csvrow =[tracesFileName, self.timeOut, None, None]
					else:
						csvrow = row_list[0]#this file has not timed out

				csvInfo.append(csvrow)

			writer.writerows(csvInfo)




def main():
	parser = argparse.ArgumentParser()

	parser.add_argument('--traces_folder', dest='traces_folder', default = 'few_traces/')
	parser.add_argument('--timeout', dest='timeout', default = 900)
	parser.add_argument('--test_sat_method', dest='test_sat_method', action='store_true', default = True)
	parser.add_argument('--test_dt_method', dest='test_dt_method', action='store_true', default = False)
	parser.add_argument('-c', dest='compile_results', action='store_true', default=False)


	args,unknown = parser.parse_known_args()

	#print(dict(args))

	tracesFolderName = args.traces_folder
	timeout = int(args.timeout)
	compile_results = bool(args.compile_results)
	method = 'SAT' if bool(args.test_sat_method) else 'DT'

	m = multiprocess(tracesFolderName, method, timeout)

	if not compile_results:
		m.populate_queue()#comment this out for compiling results
	else:
		m.compile_results()#uncomment this for compiling results



if __name__ == '__main__':
    main() 
