import sys
import pdb
from utils.SimpleTree import SimpleTree, Formula, DecisionTreeFormula
import io
import re
import itertools
import contextlib


def lineToTrace(line):
    line = line.strip()
    kwargs = dict()
    suffix = ''
    try:
        traceData, suffix = line.split('::')
    except ValueError:
        traceData = line
    match = re.fullmatch(r'(?P<lassoStart>-?\d+)?(?:\[(?P<weight>)\d+])?', suffix)
    if match.group('lassoStart') is not None: kwargs['lassoStart'] = int(match.group('lassoStart'))
    if match.group('weight') is not None: kwargs['weight'] = int(match.group('weight'))
    traceVector = [[bool(int(varValue)) for varValue in varsInTimestep.split(',')] for varsInTimestep in
                   traceData.split(';')]
    trace = Trace(traceVector, **kwargs)
    return trace


class Trace:
    def __init__(self, traceVector, lassoStart=None, intendedEvaluation=None, literals=None, weight=1):

        self.lengthOfTrace = len(traceVector)
        self.intendedEvaluation = intendedEvaluation
        if lassoStart is not None:
            self.lassoStart = int(lassoStart)
            if self.lassoStart < 0: self.lassoStart += self.lengthOfTrace
            if self.lassoStart >= self.lengthOfTrace:
                pdb.set_trace()
                raise Exception(
                    "lasso start = %s is greater than any value in trace (trace length = %s) -- must be smaller" % (
                    self.lassoStart, self.lengthOfTrace))
        else:
            self.lassoStart = None
        assert self.lassoStart is None or self.lengthOfTrace > 0 and self.lassoStart <= self.lengthOfTrace
        self.numVariables = len(traceVector[0])
        self.traceVector = traceVector
        if literals == None:
            # pdb.set_trace()
            self.literals = ["x" + str(i) for i in range(self.numVariables)]
        else:
            self.literals = literals
        self.weight = weight

    def __repr__(self):
        return repr(self.traceVector) + "\n" + repr(self.lassoStart) + "\n\n"

    def __str__(self):
        sequence = ';'.join(','.join(f'{int(k)}' for k in t) for t in self.traceVector)
        suffix = ''
        if self.lassoStart is not None: suffix = f'{suffix}{self.lassoStart}'
        if self.weight is not None and self.weight != 1: suffix = f'{suffix}[{self.weight}]'
        if suffix: sequence = f"{sequence}::{suffix}"
        return sequence

    def nextPos(self, currentPos):
        if currentPos is None:
            return None
        if currentPos == self.lengthOfTrace - 1:
            return self.lassoStart
        else:
            return currentPos + 1


    def futurePos(self, currentPos):
        futurePositions = []
        alreadyGathered = set()
        while currentPos not in alreadyGathered:
            if currentPos is None: break
            futurePositions.append(currentPos)
            alreadyGathered.add(currentPos)
            currentPos = self.nextPos(currentPos)
        # else:
        #     # always add a new one so that all the next-relations are captured
        #     futurePositions.append(currentPos)
        return futurePositions

    def evaluateFormulaOnTrace(self, formula):

        if isinstance(formula, Formula):

            nodes = list(set(formula.getAllNodes()))
            self.truthAssignmentTable = {node: [None for _ in range(self.lengthOfTrace)] for node in nodes}

            for i in range(self.numVariables):
                literalFormula = Formula(self.literals[i])

                self.truthAssignmentTable[literalFormula] = [bool(measurement[i]) for measurement in self.traceVector]

            return self.__truthValue(formula, 0)

        elif isinstance(formula, DecisionTreeFormula):
            truthValue = None
            tree = formula
            while tree is not None:
                truthValue = self.evaluateFormulaOnTrace(tree.label)
                tree = tree.left if truthValue else tree.right
            return truthValue

        else:
            raise NotImplementedError(f"evaluating {type(formula)}")


    def __truthValue(self, formula, timestep):
        if timestep is None:
            return False
        futureTracePositions = self.futurePos(timestep)
        tableValue = self.truthAssignmentTable[formula][timestep]
        if tableValue != None:
            return tableValue
        else:
            label = formula.label
            if label == '&':
                return self.__truthValue(formula.left, timestep) and self.__truthValue(formula.right, timestep)
            elif label == '|':
                return self.__truthValue(formula.left, timestep) or self.__truthValue(formula.right, timestep)
            elif label == '!':
                return not self.__truthValue(formula.left, timestep)
            elif label == '->':
                return not self.__truthValue(formula.left, timestep) or self.__truthValue(formula.right, timestep)
            elif label == 'F':
                return max([self.__truthValue(formula.left, futureTimestep) for futureTimestep in futureTracePositions])
                # return self.__truthValue(formula.left, timestep) or self.__truthValue(formula, self.nextPos(timestep))
            elif label == 'G':
                return min([self.__truthValue(formula.left, futureTimestep) for futureTimestep in futureTracePositions])
                # return self.__truthValue(formula.left, timestep) and not self.__truthValue(formula, self.nextPos(timestep))
            elif label == 'U':
                return max(
                    [self.__truthValue(formula.right, futureTimestep) for futureTimestep in futureTracePositions]) == True \
                       and ( \
                                   self.__truthValue(formula.right, timestep) \
                                   or \
                                   (self.__truthValue(formula.left, timestep) and self.__truthValue(formula,
                                                                                                self.nextPos(timestep))) \
                           )
            elif label == 'X':
                return self.__truthValue(formula.left, self.nextPos(timestep))
            elif label == 'true':
                return True
            elif label == 'false':
                return False
            else:
                raise NotImplementedError(f"evaluation of operator {label!r}")


defaultOperators = ['G', 'F', '!', 'U', '&', '|', '->', 'X']


class ExperimentTraces:
    def __init__(self, *,
        tracesToAccept=None,
        tracesToReject=None,
        operators=['G', 'F', '!', 'U', '&', '|', '->', 'X'],
        depth=None,
        possibleSolution=None,
        numVariables=None,
    ):
        self.acceptedTraces = tracesToAccept if tracesToAccept is not None else []
        self.rejectedTraces = tracesToReject if tracesToReject is not None else []
        self.numVariables = numVariables
        if tracesToAccept != None and tracesToAccept != None:
            self.maxLengthOfTraces = 0
            for trace in self.acceptedTraces + self.rejectedTraces:
                if trace.lengthOfTrace > self.maxLengthOfTraces:
                    self.maxLengthOfTraces = trace.lengthOfTrace
            if self.numVariables is None:
                try:
                    self.numVariables = self.acceptedTraces[0].numVariables
                except:
                    self.numVariables = self.rejectedTraces[0].numVariables

        self.operators = operators
        self.depthOfSolution = depth
        self.possibleSolution = possibleSolution

    def __len__(self):
        return len(self.acceptedTraces) + len(self.rejectedTraces)

    def __iter__(self):
        return itertools.chain(self.acceptedTraces, self.rejectedTraces)

    def isFormulaConsistent(self, f):

        # not checking consistency in the case that traces are contradictory
        if f == None:
            return True
        for accTrace in self.acceptedTraces:
            if not accTrace.evaluateFormulaOnTrace(f):
                return False
        for rejTrace in self.rejectedTraces:
            if rejTrace.evaluateFormulaOnTrace(f):
                return False
        return True

    def split(self, filter):
        """ Split the traces in two.
            :param filter: function(trace:Trace, label:bool)->bool
            :return: (filtered_true, filtered_false)
            :rtype: (ExperimentTraces, ExperimentTraces)
        """
        split = dict()
        for label, traces in [
            (True,  self.acceptedTraces),
            (False, self.rejectedTraces),
        ]:
            split[label] = {True: [], False: [],}
            for trace in traces:
                split[label][bool(filter(trace, label))].append(trace)
        ans = []
        for value in (True, False):
            traces = __class__(
                numVariables=self.numVariables,
                tracesToAccept=split[True][value],
                tracesToReject=split[False][value],
                operators=self.operators,
                depth=self.depthOfSolution,
                possibleSolution=self.possibleSolution,
            )
            ans.append(traces)
        return tuple(ans)


    def splitEval(self, f):
        """ Split the traces accordigly to evaluation.
            :return: (accepted_traces, rejected_traces)
            :rtype: (ExperimentTraces, ExperimentTraces)
        """
        return self.split(lambda t,l: t.evaluateFormulaOnTrace(f))
    def splitCorrect(self, f):
        """ Split the traces accordigly to correctness.
            :return: (classified_traces, misclassified_traces)
            :rtype: (ExperimentTraces, ExperimentTraces)
        """
        return self.split(lambda t,l: t.evaluateFormulaOnTrace(f)==l)

    @property
    def positive(self):
        return __class__(
            numVariables=self.numVariables,
            tracesToAccept=self.acceptedTraces,
            operators=self.operators,
            depth=self.depthOfSolution,
            possibleSolution=self.possibleSolution,
        )
    @property
    def negative(self):
        return __class__(
            numVariables=self.numVariables,
            tracesToAccept=self.rejectedTraces,
            operators=self.operators,
            depth=self.depthOfSolution,
            possibleSolution=self.possibleSolution,
        )
    @property
    def weight(self):
        return sum(trace.weight for trace in self)

    def get_score(self, f, score='count'):
        good, bad = self.splitCorrect(f)
        if score == 'count':
            return  good.weight / self.weight
        elif score == 'ratio':
            return 0.5 * good.positive.weight / self.positive.weight + 0.5 * good.negative.weight / self.negative.weight
        else:
            msg = f'score={score!r}'
            raise NotImplementedError(msg)

    def get_misclassification(self, f):
        return 1-self.get_score(f, score='count')


    def __repr__(self):
        returnString = ""
        returnString += "accepted traces:\n"
        for trace in self.acceptedTraces:
            returnString += repr(trace)
        returnString += "\nrejected traces:\n"

        for trace in self.rejectedTraces:
            returnString += repr(trace)
        returnString += "depth of solution: " + repr(self.depthOfSolution) + "\n"
        return returnString

    def __str__(self):
        with io.StringIO() as stream:
            self.writeTraces(stream)
            return stream.getvalue()

    def writeTraces(self, tracesFileName=sys.stdout, only_traces=False):
        if isinstance(tracesFileName, str): cm = open(tracesFileName, "w")
        # else: cm = contextlib.nullcontext(tracesFileName)
        else: cm = contextlib.contextmanager(lambda: (yield tracesFileName))()
        with cm as tracesFile:
            for accTrace in self.acceptedTraces:
                line = str(accTrace) + "\n"
                tracesFile.write(line)
            tracesFile.write("---\n")
            for rejTrace in self.rejectedTraces:
                line = str(rejTrace) + "\n"
                tracesFile.write(line)
            if only_traces: return
            tracesFile.write("---\n")
            tracesFile.write(','.join(self.operators) + '\n')
            tracesFile.write("---\n")
            tracesFile.write(str(self.depthOfSolution) + '\n')
            tracesFile.write("---\n")
            tracesFile.write(str(self.possibleSolution))

    def _flieLiteralsStringToVector(self, v, literals):
        vec = []
        for l in literals:
            if l in v:
                vec.append(1)
            else:
                vec.append(0)
        return vec

    def _flieTraceToTrace(self, tracesString):
        try:
            (initPart, lasso) = tracesString.split("|")
        except:
            raise Exception("every trace has to have initial part and a lasso part")
        initPart = initPart.split(";")
        lasso = lasso.split(";")
        lassStart = len(initPart)
        traceVector = [self._flieLiteralsStringToVector(v, self.literals) for v in initPart + lasso]
        return Trace(traceVector, lassStart, literals=self.literals)

    def _getLiteralsFromData(self, data):

        for tr in data:
            try:
                (initPart, lasso) = tr.split("|")
            except:
                raise Exception("every trace has to have initial part and a lasso part")
            initPart = initPart.split(";")
            lasso = lasso.split(";")
            for tmstp in initPart + lasso:
                lits = tmstp.split(",")
                for lit in lits:
                    lit = lit.strip()
                    if not lit == "null" and not lit in self.literals:
                        self.literals.append(lit)

    def readTracesFromFlieJson(self, data):

        positive = data["positive"]
        negative = data["negative"]
        self.literals = []
        try:
            self.literals = data["literals"]
        except:
            self._getLiteralsFromData(positive)
            self._getLiteralsFromData(negative)

        self.numVariables = len(self.literals)
        try:
            self.operators = data["operators"]
        except:
            self.operators = defaultOperators

        for tr in positive:
            trace = self._flieTraceToTrace(tr)
            self.acceptedTraces.append(trace)
        for tr in negative:
            trace = self._flieTraceToTrace(tr)
            self.rejectedTraces.append(trace)

    def readTracesFromString(self, s):
        with io.StringIO(s) as stream:
            self.readTracesFromStream(stream)

    def readTracesFromStream(self, stream):

        readingMode = 0

        operators = None
        for line in stream:
            lassoStart = None
            if '---' in line:
                readingMode += 1
            else:
                if readingMode == 0:

                    trace = lineToTrace(line)
                    trace.intendedEvaluation = True

                    self.acceptedTraces.append(trace)

                elif readingMode == 1:
                    trace = lineToTrace(line)
                    trace.intendedEvaluation = False
                    self.rejectedTraces.append(trace)

                elif readingMode == 2:
                    operators = [s.strip() for s in line.split(',')]

                elif readingMode == 3:
                    self.depthOfSolution = int(line)
                elif readingMode == 4:
                    possibleSolution = line.strip()
                    if possibleSolution.lower() == "none":
                        self.possibleSolution = None
                    else:
                        self.possibleSolution = Formula.convertTextToFormula(possibleSolution)

                else:
                    break
        if operators == None:
            self.operators = defaultOperators
        else:
            self.operators = operators

        self.maxLengthOfTraces = 0
        for trace in self.acceptedTraces + self.rejectedTraces:
            if trace.lengthOfTrace > self.maxLengthOfTraces:
                self.maxLengthOfTraces = trace.lengthOfTrace

        # an assumption that number of variables is the same across all the traces
        try:
            self.numVariables = self.acceptedTraces[0].numVariables
        except:
            self.numVariables = self.rejectedTraces[0].numVariables
        for trace in self.acceptedTraces + self.rejectedTraces:
            if trace.numVariables != self.numVariables:
                raise Exception("wrong number of variables")

    def readTracesFromFile(self, tracesFileName):
        with open(tracesFileName) as tracesFile:
            self.readTracesFromStream(tracesFile)

def parseExperimentTraces(source):
    if isinstance(source, str): cm = open(source, "r")
    # else: cm = contextlib.nullcontext(source)
    else: cm = contextlib.contextmanager(lambda: (yield source))()
    with cm as f:
        traces = ExperimentTraces()
        traces.readTracesFromStream(f)
        return traces
