import pdb
import random

from utils.SimpleTree import SimpleTree, Formula
from utils.Traces import Trace, ExperimentTraces

operatorsAndArities = {'G':1, 'F':1, '!':1, 'U':2, '&':2,'|':2, '->':2, 'X':1, 'prop':0}

def generateTracesFromFormula(formula, lengthOfTrace, minNumberOfAccepting, minNumberOfRejecting, totalMax = 20, numSuperfluousVars=1, generateExactNumberOfTraces=True,
    finiteTraces=False, misclassificationRate=0.05,
):
    allVars = formula.getAllVariables()
    allTraces = {"accepting":[], "rejecting":[]}
    numberOfVars = len(allVars) + numSuperfluousVars
    depthOfFormula = formula.getDepth()
    totalNumberOfTrials = 0
    random.seed(
)    
    while (len(allTraces["accepting"]) < minNumberOfAccepting or len(allTraces["rejecting"]) < minNumberOfRejecting)\
    and len(allTraces["accepting"]) + len(allTraces["rejecting"]) < totalMax: 
        
        lassoStart = None if finiteTraces else random.randint( 0, lengthOfTrace-1 )
        traceVector = [ [random.randint(0,1) for _ in range(numberOfVars)] for _ in range(lengthOfTrace) ] 
        
        trace = Trace(traceVector, lassoStart)
        totalNumberOfTrials += 1
        
        if generateExactNumberOfTraces == True and totalNumberOfTrials > totalMax:
            break
        if trace.evaluateFormulaOnTrace(formula) == True:
            if generateExactNumberOfTraces == True and len(allTraces["accepting"]) == minNumberOfAccepting:
                continue
            allTraces["accepting"].append(trace)
        else:
            if generateExactNumberOfTraces == True and len(allTraces["rejecting"]) == minNumberOfRejecting:
                continue
            allTraces["rejecting"].append(trace)


    if misclassificationRate>0:
        #randomly select some examples
        numTraces = len(allTraces["accepting"])+len(allTraces["rejecting"])
        numSwaps = max(1, int(numTraces*misclassificationRate))

        numFalseNeg = min(len(allTraces["accepting"]), random.randint(1, numSwaps))
        numFalsePos = random.randint(1, numSwaps)


        falseNeg = allTraces["accepting"][-numFalseNeg:]
        falsePos = allTraces["rejecting"][-numFalsePos:]

        allTraces = {
            "accepting": allTraces["accepting"][:numFalseNeg] + falsePos,
            "rejecting": allTraces["rejecting"][:numFalsePos] + falseNeg,
        }

        random.shuffle(allTraces["accepting"])
        random.shuffle(allTraces["rejecting"])

    traces = ExperimentTraces(tracesToAccept=allTraces["accepting"], tracesToReject=allTraces["rejecting"], depth = depthOfFormula, possibleSolution = formula)
    return traces

        
    
    

