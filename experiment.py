#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pdb
from z3 import *
import argparse
from smtEncoding.dagSATEncoding import DagSATEncoding
import os
from solverRuns import run_solver, run_rec_dt, run_dt_solver
from utils.Traces import Trace, ExperimentTraces, parseExperimentTraces
from multiprocessing import Process, Queue
import logging

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-f", "--traces",
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
    parser.add_argument("--test_rec_dt",
        dest='testRecDtMethod', default=False,
        action='store_true',
    )
    parser.add_argument("--misclassification", metavar="R",
        dest="misclassification", default=0,
        type=float,
        help="formula should have a misclassification <= R",
    )

    group_sat = parser.add_argument_group('sat method arguments')
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
        dest='iterationStep', default=1,
        type=int,
        help="increment formula size by I at each iteration",
    )
    group_maxsat = group_sat
    group_maxsat.add_argument("--optimize_depth", metavar="I",
        dest='optimizeDepth', default=float("inf"),
        type=int,
        help="use optimizer for formula size >= I",
    )
    group_maxsat.add_argument("--optimize", #metavar="SCORE",
        dest='optimize', default='count',
        choices=['count', 'ratio'],
        help="score to optimize",
    )
    group_maxsat.add_argument("--min_score", metavar="S",
        dest='minScore', default=0,
        type=float,
        help="formula should achieve a score >= S",
    )
    group_sat.add_argument("--max_num_formulas", metavar="N",
        dest='numFormulas', default=1,
        type=int,
    )

    group_dt = parser.add_argument_group('dt method arguments')

    parser.add_argument("--timeout", metavar="T",
        dest='timeout', default=float("inf"),
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

    if args.testSatMethod:
        formulas, timePassed = run_solver(
            traces=traces,
            startDepth=args.startDepth, maxDepth=args.maxDepth, step=args.iterationStep,
            optimizeDepth=args.optimizeDepth,
            optimize=args.optimize, minScore=args.minScore,
            maxNumModels=args.numFormulas,
            timeout=args.timeout,
        )
        logging.info(f"formulas: {[f.prettyPrint() for f in formulas]}, timePassed: {timePassed}")

    if args.testRecDtMethod:
        formula, timePassed = run_rec_dt(
            traces=traces,
            startDepth=args.startDepth, maxDepth=args.maxDepth, step=args.iterationStep,
            optimizeDepth=args.optimizeDepth,
            optimize=args.optimize, minScore=args.minScore,
            misclassification=args.misclassification,
            timeout=args.timeout,
        )
        trimedFormula = formula.trimPseudoNodes()
        flatFormula = trimedFormula.flattenToFormula()
        logging.debug(f"formula: {formula.prettyPrint()}")
        # logging.debug(f"DT formulas: {flatFormula.prettyPrint()}, timePassed: {timePassed}")
        logging.info(f"timePassed: {timePassed}, completeDT: {trimedFormula is formula}, sizeDT: {trimedFormula.getSize()}, depthDT: {trimedFormula.getDepth()}, misclassification: {traces.get_misclassification(trimedFormula)}")
        # logging.info(f"misclassification: {traces.get_misclassification(flatFormula)}")
        # good, bad = traces.splitCorrect(trimedFormula)
        # print
        # good.writeTraces(only_traces=True)
        # print('===')
        # bad.writeTraces(only_traces=True)

    if args.testDtMethod:

        timePassed, numAtoms, numPrimitives = run_dt_solver(
            traces=traces,
            misclassification=args.misclassification,
        )
        logging.info(f"timePassed: {timePassed}, numAtoms: {numAtoms}, numPrimitives: {numPrimitives}")



if __name__ == "__main__":
    main()
