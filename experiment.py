#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdb
from z3 import *
import argparse
from smtEncoding.dagSATEncoding import DagSATEncoding
import os
from solverRuns import run_solver, run_dt_solver
from utils.Traces import Trace, ExperimentTraces, parseExperimentTraces
from multiprocessing import Process, Queue
import logging

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--traces",
        dest='tracesFileName',
        default="traces/dummy.trace",
    )
    parser.add_argument("--test_sat_method",
        dest='testSatMethod', default=False,
        action='store_true',
    )
    parser.add_argument("--test_dt_method",
        dest='testDtMethod', default=False,
        action='store_true',
    )
    group_sat = parser.add_argument_group('sat method arguments')
    group_sat.add_argument("--max_depth", metavar="N",
        dest='maxDepth', default=8,
        type=int,
    )
    group_sat.add_argument("--start_depth", metavar="N",
        dest='startDepth', default=1,
        type=int,
    )
    group_sat.add_argument("--max_num_formulas", metavar="N",
        dest='numFormulas', default=1,
        type=int,
    )
    group_sat.add_argument("--iteration_step", metavar="N",
        dest='iterationStep', default=1,
        type=int,
    )
    parser.add_argument("--timeout", metavar="T",
        dest='timeout', default=600,
        type=int,
        help="timeout in seconds",
    )
    parser.add_argument("--log", metavar="LVL",
        dest='loglevel', default="INFO",
        # choices="DEBUG, INFO, WARNING, ERROR, CRITICAL".split(", "),
        help="log level, usually in DEBUG, INFO, WARNING, ERROR, CRITICAL",
    )
    args,unknown = parser.parse_known_args()
    tracesFileName = args.tracesFileName
    # args = vars(args) # Namespace to dict
    # args = {arg:val for arg,val in args.items() if val is not None} # filter out missing parameters


    """
    traces is
     - list of different recorded values (traces)
     - each trace is a list of recordings at time units (time points)
     - each time point is a list of variable values (x1,..., xk)
    """

    # numeric_level = getattr(logging, args.loglevel.upper())
    numeric_level = args.loglevel.upper()
    logging.basicConfig(level=numeric_level)

    traces = parseExperimentTraces(args.tracesFileName)
    #print(traces)

    # numFormulas   = args.numFormulas
    # startDepth    = args.startDepth
    # maxDepth      = args.maxDepth
    # finalDepth    = args.maxDepth
    # iterationStep = args.iterationStep

    # solvingTimeout = args.timeout
    # timeout = args.timeout

    if args.testSatMethod:
        formulas, timePassed = run_solver(
            traces=traces,
            maxNumOfFormulas=args.numFormulas,
            startValue=args.startDepth,
            finalDepth=args.maxDepth,
            step=args.iterationStep,
        )
        logging.info("formulas: "+str([f.prettyPrint(f) for f in formulas])+", timePassed: "+str(timePassed))


    if args.testDtMethod:

        timePassed, numAtoms, numPrimitives = run_dt_solver(
            traces=traces,
        )
        logging.info(f"timePassed: {timePassed}, numAtoms: {numAtoms}, numPrimitives: {numPrimitives}")





if __name__ == "__main__":
    main()
