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
                score = traces.get_score(formula, fg.optimize)
                if score < minScore:
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
    format_log = lambda traces: f"recdt on (pos+neg)={len(traces.positive)}+{len(traces.negative)}={len(traces)} traces"
    log_level = logging.INFO
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

    while queue:
        nodeTraces, node = queue_pop()

        if len(nodeTraces)==0:
            logging.log(log_level, f"{format_log(nodeTraces)}: Skipping.")
            childnode.label="?"
            continue

        for leafFormula in [Formula('true'), Formula('false')]:
            stopping_criterion = nodeTraces.get_misclassification(leafFormula) <= misclassification
            if stopping_criterion:
                logging.log(log_level, f"{format_log(nodeTraces)}: Stopping criterion reached.")
                node.label = leafFormula
                stopping = True
                break
        else: stopping = False
        if stopping: continue

        logging.log(log_level, f"{format_log(nodeTraces)}: Solving...")
        formulas = get_models(
            traces=nodeTraces,
            **solver_args,
            maxNumModels=1,
            timeout=timeout-tictoc_total.tocvalue(),
        )
        if len(formulas)<1: # timeout
            if not return_partial:
                return None
            break
        node.label = formula = formulas[0]
        accTraces, rejTraces = nodeTraces.splitEval(formula)

        for subTraces, child in [
            (accTraces, "left" ),
            (rejTraces, "right"),
        ]:
            childnode = DecisionTreeFormula(label="?")
            setattr(node, child, childnode)

            if len(subTraces) == len(nodeTraces):
                logging.warning(f"{format_log(subTraces)}: {child} child got all the traces, aborting this branch exploration!")
                childnode.label="..."
                if not return_partial:
                    msg = f"Ineffective split between {len(nodeTraces)} traces with formula {formula.prettyPrint()}."
                    raise RuntimeError(msg)
                    return None
                continue

            logging.debug(f"{format_log(subTraces)}: processing {child} child later...")
            queue_push(subTraces, childnode)

    return result
