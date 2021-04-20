from smtEncoding.dagSATEncoding import DagSATEncoding
from z3 import *
import sys
import pdb
import traceback
import logging
from collections import deque
import heapq
from random import random
from pytictoc import TicToc
from utils.SimpleTree import Formula, DecisionTreeFormula

def get_models(
    traces,
    startDepth=1, maxDepth=float("inf"), step=1,
    optimizeDepth=float("inf"),
    optimize='count', minScore=0,
    encoder=DagSATEncoding,
    maxNumModels=1,
    timeout=float("inf"),
):
    if optimizeDepth < maxDepth and optimize is None:
        logging.warning("Optimize objective not set. Ignoring optimization.")
    tictoc_z3, time_z3 = TicToc(), 0
    tictoc_total = TicToc()
    tictoc_total.tic()
    results = []
    i = startDepth
    fg = encoder(i, traces)
    fg.encodeFormula(optimize=(optimize if i>=optimizeDepth else None))

    while len(results) < maxNumModels and i < maxDepth:
        if fg.set_timeout(timeout-tictoc_total.tocvalue()) <= 0: break
        tictoc_z3.tic()
        solverRes = fg.solver.check()
        time_z3 += tictoc_z3.tocvalue()
        acceptFormula = False
        if solverRes == unsat:
            logging.debug(f"not sat for i = {i}")
        elif solverRes != sat:
            logging.debug(f"unknown for i = {i}")
            break
        else:
            acceptFormula = True
            solverModel = fg.solver.model()
            formula = fg.reconstructWholeFormula(solverModel)
            if fg.optimize:
                score = fg.optimize and traces.get_score(formula, fg.optimize)
                if score <= minScore:
                    acceptFormula = False
                    logging.debug(f"score too low for i = {i} ({fg.optimize}={score})")
        if not acceptFormula:
            i += step
            fg = encoder(i, traces)
            fg.encodeFormula(optimize=(optimize if i>=optimizeDepth else None))
        else:
            if fg.optimize:
                logging.info(f"found formula {formula.prettyPrint()} ({fg.optimize}={score})")
            else:
                logging.info(f"found formula {formula.prettyPrint()}")
            #print(f"found formula {formula}")
            formula = Formula.normalize(formula)
            logging.info(f"normalized formula {formula}")
            if formula not in results:
                results.append(formula)

            #prevent current result from being found again
            block = []
            # pdb.set_trace()
            # print(m)
            infVariables = fg.getInformativeVariables()

            logging.debug("informative variables of the model:")
            for v in infVariables:
                logging.debug((v, solverModel[v]))
            logging.debug("===========================")
            for d in solverModel:
                # d is a declaration
                if d.arity() > 0:
                    raise Z3Exception("uninterpreted functions are not supported")
                # create a constant from declaration
                c = d()
                if is_array(c) or c.sort().kind() == Z3_UNINTERPRETED_SORT:
                    raise Z3Exception("arrays and uninterpreted sorts are not supported")
                block.append(c != solverModel[d])
            fg.solver.add(Or(block))

    # time_total = tictoc_total.tocvalue()
    # time_z3
    # print(time_z3, time_total)
    return results

def get_rec_dt(
    traces,
    misclassification=0,
    search="breath",
    timeout=float("inf"),
    **solver_args,
):
    return_partial = True
    logname="recdt"
    tictoc_total = TicToc()
    tictoc_total.tic()


    if search in {"depth","breath"}:
        queue = deque()
        queue_push = lambda nodeTraces, node: queue.append((nodeTraces, node))
        if   search=="depth":  queue_pop = queue.pop
        elif search=="breath": queue_pop = queue.popleft
    elif search=="priority":
        queue = []
        queue_push = lambda nodeTraces, node: heapq.heappush(queue, ((-len(traces), random()), nodeTraces, node))
        queue_pop  = lambda : heapq.heappop(queue)[1:]
    else:
        raise NotImplementedError(f"tree search: {search!r}")

    result = DecisionTreeFormula(label="?")
    queue_push(traces, result)
    i=0
    while queue:
        nodeTraces, node = queue_pop()

        positive_ratio = float(len(nodeTraces.positive)/(len(nodeTraces.positive)+len(nodeTraces.negative)))
        negative_ratio = 1-positive_ratio
        if (positive_ratio <= misclassification) or (negative_ratio <= misclassification):

            logging.debug(f"{logname}:Stopping criterion reached with {len(nodeTraces.positive)} positives and {len(nodeTraces.negative)} negatives, it was effective!")
            if positive_ratio <= misclassification:
                node.label = Formula('false')
            else:
                node.label = Formula('true')
            #childnode = DecisionTreeFormula(label="?")
            #setattr(node, child, childnode)
            continue

        logging.debug(f"{logname}:solving on (pos+neg)={len(nodeTraces.positive)}+{len(nodeTraces.negative)}={len(nodeTraces)} traces...")

        formulas = get_models(
            traces=nodeTraces,
            **solver_args,
            maxNumModels=1,
            timeout=timeout-tictoc_total.tocvalue(),
        )
        if len(formulas)<1: # timeout
            if not(return_partial):
                return None
            break
        node.label = formula = formulas[0]
        accTraces, rejTraces = nodeTraces.splitEval(formula)
        
        i+=1
        subbranches = []
        for subTraces, child in [
            (accTraces, "left" ),
            (rejTraces, "right"),
        ]:

            if len(subTraces)==0 or len(subTraces) == len(nodeTraces):
                
                logging.warning(f"{logname}:{child} child got {len(subTraces.positive)}+{len(subTraces.negative)}={len(subTraces)} traces, it was ineffective!")
                childnode.label="..."
                if not(return_partial):
                    msg = f"Ineffective split between {len(nodeTraces)} traces with formula {formula.prettyPrint()}."
                    raise RuntimeError(msg)
                    break
                continue
            else:
                logging.debug(f"{logname}:{child} child got {len(subTraces.positive)}+{len(subTraces.negative)}={len(subTraces)} traces, processing it later.")

            
            childnode = DecisionTreeFormula(label="?")
            setattr(node, child, childnode)
            
            queue_push(subTraces, childnode)

    return result
