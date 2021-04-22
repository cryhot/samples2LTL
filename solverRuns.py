import sys
from multiprocessing import Process, Queue
from smtEncoding.dagSATEncoding import DagSATEncoding
from pytictoc import TicToc
from z3 import *
import pdb
from utils import config
from formulaBuilder.DTFormulaBuilder import DTFormulaBuilder
from formulaBuilder.AtomBuilder import AtomBuilder, AtomBuildingStrategy
from formulaBuilder.satQuerying import get_models, get_rec_dt

def run_solver(*,
    q=None,
    encoder=DagSATEncoding,
    **solver_args,
):
    separate_process = q is not None

    t = TicToc()
    t.tic()
    results = get_models(encoder=encoder, **solver_args)
    time_passed = t.tocvalue()

    if separate_process == True:
        q.put([results, time_passed])
    else:
        return [results, time_passed]

def run_rec_dt(*,
    traces,
    q=None,
    encoder=DagSATEncoding,
    **solver_args,
):
    separate_process = q is not None

    t = TicToc()
    t.tic()
    result = get_rec_dt(traces=traces, encoder=encoder, **solver_args)
    time_passed = t.tocvalue()

    result.writeDotFile("recdt.dot", traces=traces)

    if separate_process == True:
        q.put([result, time_passed])
    else:
        return [result, time_passed]



def run_dt_solver(
    traces,
    subsetSize=config.DT_SUBSET_SIZE,
    txtFile="treeRepresentation.txt",
    strategy=config.DT_SAMPLING_STRATEGY,
    decreaseRate=config.DT_DECREASE_RATE,
    repetitionsInsideSampling=config.DT_REPETITIONS_INSIDE_SAMPLING,
    restartsOfSampling=config.DT_RESTARTS_OF_SAMPLING,
    q=None,
    encoder=DagSATEncoding,
    misclassification=0,
    timeout=float("inf"),
    record_result=dict(), # output
):

    #try:
        config.encoder = encoder
        separate_process = q is not None
        ab = AtomBuilder()
        ab.getExamplesFromTraces(traces)
        #samplingStrategy = config.DT_SAMPLING_STRATEGY
        samplingStrategy = strategy
        #decreaseRate = config.DT_DECREASE_RATE
        decreaseRate = decreaseRate
        t = TicToc()
        t.tic()
        (atoms, atomTraceEvaluation) = ab.buildAtoms(
            sizeOfPSubset=subsetSize,
            strategy=samplingStrategy,
            sizeOfNSubset=subsetSize,
            probabilityDecreaseRate=decreaseRate,
            numRepetitionsInsideSampling=repetitionsInsideSampling,
            numRestartsOfSampling=restartsOfSampling,
            timeout=timeout-t.tocvalue(),
        )

        fb = DTFormulaBuilder(
            features=ab.atoms,
            data=ab.getMatrixRepresentation(),
            labels=ab.getLabels(),
            stoppingVal=misclassification,
            # timeout=timeout-t.tocvalue(), #TODO
        )
        fb.createASeparatingFormula()
        timePassed = t.tocvalue()
        atomsFile = "atoms.txt"
        treeTxtFile = txtFile
        ab.writeAtomsIntoFile(atomsFile)


        numberOfUsedPrimitives = fb.numberOfNodes()
        fb.tree_to_text_file(treeTxtFile)
        fb.tree_to_dot_file("atoms.dot")
        record_result['formulaTree'] = fb.tree_to_DecisionTreeFormula()
    #    return (timePassed, len(atoms), numberOfUsedPrimitives)
        if separate_process:
            q.put([timePassed, len(atoms), numberOfUsedPrimitives])
        else:
            return [timePassed, len(atoms), numberOfUsedPrimitives]
#     except Exception as e:
#         print(e)
#         sys.exit(1)
