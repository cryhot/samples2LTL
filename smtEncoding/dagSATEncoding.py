from z3 import *
import pdb
import itertools
from utils.SimpleTree import SimpleTree, Formula

class DagSATEncoding:
    """
    - D is the depth of the tree
    - lassoStartPosition denotes the position when the trace values start looping
    - traces is
      - list of different recorded values (trace)
      - each trace is a list of recordings at time units (time point)
      - each time point is a list of variable values (x1,..., xk)
    """
    def __init__(self, D, testTraces, using_optimize=False):

        defaultOperators = ['G', 'F', '!', 'U', '&','|', '->', 'X']
        unary = ['G', 'F', '!', 'X']
        binary = ['&', '|', 'U', '->']
        #except for the operators, the nodes of the "syntax table" are additionally the propositional variables

        if testTraces.operators == None:
            self.listOfOperators = defaultOperators
        else:
            self.listOfOperators = testTraces.operators

        if 'prop' in self.listOfOperators:
            self.listOfOperators.remove('prop')


        self.unaryOperators = [op for op in self.listOfOperators if op in unary]
        self.binaryOperators = [op for op in self.listOfOperators if op in binary]

        #self.noneOperator = 'none' # a none operator is not needed in this encoding


        self.formulaDepth = D


        #traces = [t.traceVector for t in testTraces]

        self.traces = testTraces

        self.listOfVariables = [i for i in range(self.traces.numVariables)]




        #keeping track of which positions in a tree (and in time) are visited, so that constraints are not generated twice
#        self.visitedPositions = set()


    def getInformativeVariables(self):
        res = []
        res += [v for v in self.x.values()]
        res += [v for v in self.l.values()]
        res += [v for v in self.r.values()]


        return res
    """
    the working variables are
        - x[i][o]: i is a subformula (row) identifier, o is an operator or a propositional variable. Meaning is "subformula i is an operator (variable) o"
        - l[i][j]:  "left operand of subformula i is subformula j"
        - r[i][j]: "right operand of subformula i is subformula j"
        - y[i][tr][t]: semantics of formula i in time point t of trace tr
        :param optimize: None|"count"|"ratio"
    """
    def encodeFormula(self,
        # unsatCore=True,
        optimize=None,
    ):
        self.operatorsAndVariables = self.listOfOperators + self.listOfVariables

        self.x = {
            (i, o): Bool(f'x_{i}_{o}')
            for i in range(self.formulaDepth)
            for o in self.operatorsAndVariables
        }
        self.l = {
            (parentOperator, childOperator): Bool(f'l_{parentOperator}_{childOperator}')
            for parentOperator in range(1, self.formulaDepth)
            for childOperator in range(parentOperator)
        }
        self.r = {
            (parentOperator, childOperator): Bool(f'r_{parentOperator}_{childOperator}')
            for parentOperator in range(1, self.formulaDepth)
            for childOperator in range(parentOperator)
        }

        self.y = {
            (i, traceIdx, positionInTrace): Bool(f'y_{i}_{traceIdx}_{positionInTrace}')
            for i in range(self.formulaDepth)
            for traceIdx, trace in enumerate(self.traces)
            for positionInTrace in range(trace.lengthOfTrace)
        }

        self.optimize = optimize
        if self.optimize is None:
            self.solver = Solver()
        else:
            self.solver = Optimize()
        # self.solver.set(unsat_core=unsatCore) # Optimize don't have this option

        self.exactlyOneOperator()
        self.firstOperatorVariable()

        self.propVariablesSemantics()

        self.operatorsSemantics()
        self.noDanglingVariables()

        if optimize is None:
            self.solver.assert_and_track(
                And([
                    self.y[(self.formulaDepth - 1, traceIdx, 0)]
                    for traceIdx, trace in enumerate(self.traces.acceptedTraces)
                ]),
                'accepted traces should be accepting'
            )
            self.solver.assert_and_track(
                And([
                    Not(self.y[(self.formulaDepth - 1, traceIdx, 0)])
                    for traceIdx, trace in enumerate(self.traces.rejectedTraces, start=len(self.traces.acceptedTraces))
                ]),
                'rejecting traces should be rejected'
            )
        elif optimize in ['count', 'ratio']:
            if optimize == 'count':
                # balance = 1/self.traces.weight
                balance = 1
            if optimize == 'ratio':
                # balance = 1/self.traces.positive.weight
                balance = self.traces.negative.weight
            for traceIdx, trace in enumerate(self.traces.acceptedTraces):
                self.solver.add_soft(
                    self.y[(self.formulaDepth - 1, traceIdx, 0)],
                    weight=trace.weight * balance,
                    id="count",
                )
            if optimize == 'ratio':
                # balance = 1/self.traces.negative.weight
                balance = self.traces.positive.weight
            for traceIdx, trace in enumerate(self.traces.rejectedTraces, start=len(self.traces.acceptedTraces)):
                self.solver.add_soft(
                    Not(self.y[(self.formulaDepth - 1, traceIdx, 0)]),
                    weight=trace.weight * balance,
                    id="count",
                )
        else:
            msg = f'optimize={optimize!r}'
            raise NotImplementedError(msg)

    def set_timeout(self, timeout):
        if timeout is None: timeout=float("inf")
        timeout = int(min(timeout*1000, sys.maxsize)) # in milliseconds
        self.solver.set(timeout=timeout)
        return timeout/1000


    def propVariablesSemantics(self):
        for i in range(self.formulaDepth):
            for p in self.listOfVariables:
                for traceIdx, tr in enumerate(self.traces.acceptedTraces + self.traces.rejectedTraces):
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, p)],
                            And([
                                self.y[(i,traceIdx, timestep)] if tr.traceVector[timestep][p] else Not(self.y[(i, traceIdx, timestep)])
                                for timestep in range(tr.lengthOfTrace)
                            ])
                        ),
                        f'semantics of propositional variable depth_{i} var _{p}_trace_{traceIdx}'
                    )

    def firstOperatorVariable(self):
        self.solver.assert_and_track(
            Or([
                self.x[k]
                for k in self.x if k[0] == 0 and k[1] in self.listOfVariables
            ]),
            'first operator a variable'
        )

    def noDanglingVariables(self):
        if self.formulaDepth > 0:
            self.solver.assert_and_track(
                And([
                    Or(
                        AtLeast([
                            self.l[(rowId, i)]
                            for rowId in range(i+1, self.formulaDepth)
                        ]+[1]),
                        AtLeast([
                            self.r[(rowId, i)]
                            for rowId in range(i+1, self.formulaDepth)
                        ]+[1])
                    )
                    for i in range(self.formulaDepth - 1)]
                ),
                "no dangling variables"
            )

    def exactlyOneOperator(self):


            self.solver.assert_and_track(
                And([
                    AtMost([
                        self.x[k]
                        for k in self.x if k[0] == i
                    ]+[1])
                    for i in range(self.formulaDepth)
                ]),
                "at most one operator per subformula"
            )

            self.solver.assert_and_track(
                And([
                    AtLeast([
                        self.x[k]
                        for k in self.x if k[0] == i
                    ]+[1])
                    for i in range(self.formulaDepth)
                ]),
                "at least one operator per subformula"
            )

            if (self.formulaDepth > 0):
                self.solver.assert_and_track(
                And([
                    Implies(
                        Or([
                            self.x[(i, op)]
                            for op in self.binaryOperators+self.unaryOperators
                        ]),
                        AtMost([
                            self.l[k]
                            for k in self.l if k[0] == i
                        ] +[1])
                    )
                    for i in range(1,self.formulaDepth)
                ]),
                "at most one left operator for binary and unary operators"
            )

            if (self.formulaDepth > 0):
                self.solver.assert_and_track(
                    And([
                        Implies(
                            Or([
                                self.x[(i, op)]
                                for op in self.binaryOperators + self.unaryOperators
                            ]),
                            AtLeast([
                                self.l[k]
                                for k in self.l if k[0] == i
                            ]+[1])
                        )
                        for i in range(1,self.formulaDepth)
                    ]),
                    "at least one left operator for binary and unary operators"
                )

            if (self.formulaDepth > 0):
                self.solver.assert_and_track(
                    And([
                        Implies(
                            Or([
                                self.x[(i, op)]
                                for op in self.binaryOperators
                            ]),
                            AtMost([
                                self.r[k]
                                for k in self.r if k[0] == i
                            ]+[1])
                        )
                        for i in range(1, self.formulaDepth)
                    ]),
                    "at most one right operator for binary"
                )

            if (self.formulaDepth > 0):
                self.solver.assert_and_track(
                    And([
                        Implies(
                            Or([
                                self.x[(i, op)]
                                for op in self.binaryOperators
                            ]),
                            AtLeast([
                                self.r[k]
                                for k in self.r if k[0] == i
                            ]+[1])
                        )
                        for i in range(1, self.formulaDepth)
                    ]),
                    "at least one right operator for binary"
                )

            if (self.formulaDepth > 0):
                self.solver.assert_and_track(
                    And([
                        Implies(
                            Or([
                                self.x[(i, op)]
                                for op in self.unaryOperators
                            ]),
                            Not(
                                Or([
                                    self.r[k]
                                    for k in self.r if k[0] == i
                                ])
                            )
                        )
                        for i in range(1, self.formulaDepth)
                    ]),
                    "no right operators for unary"
                )

            if (self.formulaDepth > 0):
                self.solver.assert_and_track(
                    And([
                        Implies(
                            Or([
                                self.x[(i, op)] for op in
                                self.listOfVariables
                            ]),
                            Not(
                                Or(
                                    Or([
                                        self.r[k]
                                        for k in self.r if k[0] == i
                                    ]),
                                    Or([
                                        self.l[k]
                                        for k in self.l if k[0] == i
                                    ])
                                )
                            )
                        )
                        for i in range(1, self.formulaDepth)
                    ]),
                    "no left or right children for variables"
                )


    def operatorsSemantics(self):

        for traceIdx, tr in enumerate(self.traces):
            for i in range(1, self.formulaDepth):

                if '|' in self.listOfOperators:
                    #disjunction
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, '|')],
                            And([
                                Implies(
                                    And([
                                        self.l[i, leftArg],
                                        self.r[i, rightArg]
                                    ]),
                                    And([
                                        # eq(
                                            self.y[(i, traceIdx, timestep)] ==
                                            Or([
                                                self.y[(leftArg, traceIdx, timestep)],
                                                self.y[(rightArg, traceIdx, timestep)]
                                            ])
                                        # )
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for leftArg in range(i) for rightArg in range(i)
                            ])
                        ),
                        f'semantics of disjunction for trace {traceIdx} and depth {i}'
                    )

                if '&' in self.listOfOperators:
                    #conjunction
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, '&')],
                            And([
                                Implies(
                                    And([
                                        self.l[i, leftArg],
                                        self.r[i, rightArg]
                                    ]),
                                    And([
                                        self.y[(i, traceIdx, timestep)]
                                        ==
                                        And([
                                            self.y[(leftArg, traceIdx, timestep)],
                                            self.y[(rightArg, traceIdx, timestep)]
                                        ])
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for leftArg in range(i) for rightArg in range(i)
                            ])
                        ),
                        f'semantics of conjunction for trace {traceIdx} and depth {i}'
                    )

                if '->' in self.listOfOperators:
                    #implication
                    self.solver.assert_and_track(
                        Implies(self.x[(i, '->')],
                            And([
                                Implies(
                                    And([
                                        self.l[i, leftArg],
                                        self.r[i, rightArg]
                                    ]),
                                    And([
                                        self.y[(i, traceIdx, timestep)]
                                        ==
                                        Implies(
                                            self.y[(leftArg, traceIdx, timestep)],
                                            self.y[(rightArg, traceIdx, timestep)]
                                        )
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for leftArg in range(i) for rightArg in range(i)
                            ])
                        ),
                        f'semantics of implication for trace {traceIdx} and depth {i}'
                    )

                if '!' in self.listOfOperators:
                    #negation
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, '!')],
                            And([
                                Implies(
                                    self.l[(i,onlyArg)],
                                    And([
                                        self.y[(i, traceIdx, timestep)] == Not(self.y[(onlyArg, traceIdx, timestep)])
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for onlyArg in range(i)
                            ])
                        ),
                        f'semantics of negation for trace {traceIdx} and depth {i}'
                    )

                if 'G' in self.listOfOperators:
                    #globally
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, 'G')],
                            And([
                                Implies(
                                    self.l[(i,onlyArg)],
                                    And([
                                        self.y[(i, traceIdx, timestep)] ==
                                        And([
                                            self.y[(onlyArg, traceIdx, futureTimestep)]
                                            for futureTimestep in tr.futurePos(timestep)
                                        ])
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for onlyArg in range(i)
                            ])
                        ),
                        f'semantics of Globally operator for trace {traceIdx} and depth {i}'
                    )

                if 'F' in self.listOfOperators:
                    #finally
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, 'F')],
                            And([
                                Implies(
                                    self.l[(i,onlyArg)],
                                    And([
                                        self.y[(i, traceIdx, timestep)] ==
                                        Or([
                                            self.y[(onlyArg, traceIdx, futureTimestep)]
                                            for futureTimestep in tr.futurePos(timestep)
                                        ])
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for onlyArg in range(i)
                            ])
                        ),
                        f'semantics of Finally operator for trace {traceIdx} and depth {i}'
                    )

                if 'X' in self.listOfOperators:
                     #next
                     self.solver.assert_and_track(
                        Implies(
                            self.x[(i, 'X')],
                            And([
                                Implies(
                                    self.l[(i,onlyArg)],
                                    And([
                                        self.y[(i, traceIdx, timestep)] == (
                                            self.y[(onlyArg, traceIdx, tr.nextPos(timestep))] if tr.nextPos(timestep) is not None else False
                                        )
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for onlyArg in range(i)
                            ])
                        ),
                        f'semantics of neXt operator for trace {traceIdx} and depth {i}'
                    )

                if 'U' in self.listOfOperators:
                    #until
                    self.solver.assert_and_track(
                        Implies(
                            self.x[(i, 'U')],
                            And([
                                Implies(
                                    And([
                                        self.l[i, leftArg],
                                        self.r[i, rightArg]
                                    ]),
                                    And([
                                        self.y[(i, traceIdx, timestep)] ==
                                        Or([
                                            And([
                                                self.y[(leftArg, traceIdx, futurePos)]
                                                for futurePos in tr.futurePos(timestep)[0:qIndex]
                                            ]+[
                                                self.y[(rightArg, traceIdx, tr.futurePos(timestep)[qIndex])]
                                            ])
                                            for qIndex in range(len(tr.futurePos(timestep)))
                                        ])
                                        for timestep in range(tr.lengthOfTrace)
                                    ])
                                )
                                for leftArg in range(i) for rightArg in range(i)
                            ])
                        ),
                        f'semantics of Until operator for trace {traceIdx} and depth {i}'
                    )

    def reconstructWholeFormula(self, model):
        return self.reconstructFormula(self.formulaDepth-1, model)

    def reconstructFormula(self, rowId, model):
        def getValue(row, vars):
            tt = [k[1] for k in vars if k[0] == row and model[vars[k]] == True]
            if len(tt) > 1:
                raise Exception("more than one true value")
            else:
                return tt[0]
        operator = getValue(rowId, self.x)
        if operator in self.listOfVariables:
            return Formula('x'+str(operator))
        elif operator in self.unaryOperators:
            leftChild = getValue(rowId, self.l)
            return Formula([operator, self.reconstructFormula(leftChild, model)])
        elif operator in self.binaryOperators:
            leftChild = getValue(rowId, self.l)
            rightChild = getValue(rowId, self.r)
            return Formula([operator, self.reconstructFormula(leftChild,model), self.reconstructFormula(rightChild, model)])
