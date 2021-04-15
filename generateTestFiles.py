#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import pdb
import argparse
from experiments import testFileGeneration
from utils.SimpleTree import Formula
from boto.cloudformation.stack import Output

operatorsAndArities = {'G':1, 'F':1, '!':1, 'U':2, '&':2,'|':2, '->':2, 'X':1, 'prop':0}


def generateFromFormulaFile(files, outputFolder, equalNumber, traceLengths, repetitions, numFiles, counter, finiteTraces, misclassificationRate):
    for fileName in files:
        with open(fileName) as fileWithFormulas:
            counter=0
            for line in fileWithFormulas:
                f = Formula.convertTextToFormula(line)
                print("Generating traces for Formula", str(f))
                
                for minRep in repetitions:
                    for traceLength in traceLengths:
                        num=0
                        while num<numFiles:
                            generatedTraces = testFileGeneration.generateTracesFromFormula(f, traceLength, minRep, minRep, 100*minRep, finiteTraces=finiteTraces, misclassificationRate=misclassificationRate)
                            patternName = fileName.split("/")[-1]
                            patternName = patternName.split(".")[0]
                            if not os.path.exists(outputFolder+'/'+patternName):
                                os.makedirs(outputFolder+'/'+patternName)
                            testName = outputFolder+patternName+'/'+"{:04}.trace".format(counter)
                            if len(generatedTraces.acceptedTraces) > 0 and len(generatedTraces.rejectedTraces) > 0:
                                generatedTraces.writeTraces(testName)
                                counter += 1
                                num+=1

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_folder", dest="outputFolder", default="few_traces/perfect/")
    parser.add_argument("--counter_start", dest="counterStart", default=0)
    parser.add_argument("--pattern_files", dest="patternFile", default=["formulas/patterns/abscence.txt", "formulas/patterns/existence.txt", "formulas/patterns/universality.txt", "formulas/patterns/disjunctionOfExistence.txt"],\
                        nargs='+', type=str)
    parser.add_argument("--equal_number_accepting_rejecting", dest="equalNumber", default=True, action='store_true')
    parser.add_argument("--traces_set_sizes", dest="tracesSetSizes", default=[5, 10, 20, 50], nargs='+', type=int)
    parser.add_argument("--trace_lengths", dest="traceLengths", default=[5, 10], nargs='+', type=int)
    parser.add_argument("--num_files", dest="numFiles", default=1, nargs='+', type=int)
    parser.add_argument("--finite_traces", dest="finiteTraces", default=True, action='store_true')
    parser.add_argument("--misclassification_rate", dest="misclassificationRate", type=float, default=0)
    args, unknown = parser.parse_known_args()
    
    
    outputFolder = args.outputFolder
    generateFromFormulaFile(args.patternFile, outputFolder,
        equalNumber=args.equalNumber, repetitions=args.tracesSetSizes, traceLengths=args.traceLengths, numFiles=args.numFiles, counter=int(args.counterStart),
        finiteTraces=args.finiteTraces, misclassificationRate=args.misclassificationRate
    )

if __name__ == "__main__":
    main()
#     f = Formula.convertTextToFormula("|(x0,!(x1))")
#     
#     allVars = f.getAllVariables()
    
    
    
    
