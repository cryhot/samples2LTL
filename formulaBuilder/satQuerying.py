from smtEncoding.dagSATEncoding import DagSATEncoding
from z3 import *
import sys
import pdb
import traceback
import logging
from pytictoc import TicToc
from utils.SimpleTree import Formula

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
            logging.info(f"found formula {formula.prettyPrint()}"+(fg.optimize and f" ({fg.optimize}={score})"))
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
