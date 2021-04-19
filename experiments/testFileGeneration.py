import pdb
import random
import csv

from utils.SimpleTree import SimpleTree, Formula
from utils.Traces import Trace, ExperimentTraces

operatorsAndArities = {'G':1, 'F':1, '!':1, 'U':2, '&':2,'|':2, '->':2, 'X':1, 'prop':0}

def generateTracesFromFormula(formula, lengthOfTrace, minNumberOfAccepting, minNumberOfRejecting, totalMax = 20, numSuperfluousVars=1, generateExactNumberOfTraces=True,
    finiteTraces=True, misclassificationRate=0.05,
):
    allVars = formula.getAllVariables()
    allTraces = {"accepting":[], "rejecting":[]}
    numberOfVars = len(allVars) + numSuperfluousVars
    depthOfFormula = formula.getDepth()
    totalNumberOfTrials = 0
    random.seed()

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

        numFalseNeg = min(len(allTraces["accepting"]), random.randint(1, numSwaps))#at least 1 gets swapped
        numFalsePos = max(1, numSwaps - numFalseNeg) #at least 1 gets swapped


        falseNeg = allTraces["accepting"][-numFalseNeg:]
        falsePos = allTraces["rejecting"][-numFalsePos:]


        allTraces = {
            "accepting": allTraces["accepting"][:-numFalseNeg] + falsePos,
            "rejecting": allTraces["rejecting"][:-numFalsePos] + falseNeg,
        }

        random.shuffle(allTraces["accepting"])
        random.shuffle(allTraces["rejecting"])

    traces = ExperimentTraces(tracesToAccept=allTraces["accepting"], tracesToReject=allTraces["rejecting"], depth = depthOfFormula, possibleSolution = formula)
    return traces

        
    
def misclassify(traces, misclassificationRate=0.05):
    #Takes a normal sample and misclassifies

    allTraces = {"accepting": traces.acceptedTraces ,"rejecting": traces.rejectedTraces}


    if misclassificationRate>0:
        #randomly select some examples
        numTraces = len(allTraces["accepting"])+len(allTraces["rejecting"])
        numSwaps = max(1, int(numTraces*misclassificationRate))


        if numSwaps > len(allTraces["accepting"]):

            numFalseNeg = random.randint(0, len(allTraces["accepting"])-1)
            numFalsePos = numSwaps - numFalseNeg    

        elif numSwaps > len(allTraces["rejecting"]):
            numFalsePos = random.randint(0, len(allTraces["rejecting"])-1)#at least 1 gets swapped
            numFalseNeg = numSwaps - numFalsePos

        else:
            numFalseNeg = random.randint(0, numSwaps)
            numFalsePos = numSwaps - numFalseNeg
        

        falseNeg = allTraces["accepting"][:numFalseNeg]
        falsePos = allTraces["rejecting"][:numFalsePos]


        allTraces = {
            "accepting": allTraces["accepting"][numFalseNeg:] + falsePos,
            "rejecting": allTraces["rejecting"][numFalsePos:] + falseNeg,
        }

        random.shuffle(allTraces["accepting"])
        random.shuffle(allTraces["rejecting"])


    new_traces = ExperimentTraces(tracesToAccept=allTraces["accepting"], tracesToReject=allTraces["rejecting"], depth = traces.depthOfSolution, possibleSolution = traces.possibleSolution)
    return new_traces

