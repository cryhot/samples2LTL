import pdb
import re
import contextlib
from lark import Lark, Transformer
symmetric_operators = ["&", "|"]
binary_operators = ["&", "|", "U","->"]
unary_operators = ["X", "F", "G", "!"]
class SimpleTree:
    def __init__(self, label = "dummy"):
        self.left = None
        self.right = None
        self.label = label
    
    def __hash__(self):
        return hash((self.label, self.left, self.right))
    
    def __eq__(self, other):
        if other == None:
            return False
        else:
            return self.label == other.label and self.left == other.left and self.right == other.right
    
    def __ne__(self, other):
        return not self == other
    
    def _isLeaf(self):
        return self.right == None and self.left == None
    
    def _addLeftChild(self, child):
        if child == None:
            return
        if type(child) is str:
            child = SimpleTree(child)
        self.left = child
        
    def _addRightChild(self, child):
        if type(child) is str:
            child = SimpleTree(child)
        self.right = child
    
    def addChildren(self, leftChild = None, rightChild = None): 
        self._addLeftChild(leftChild)
        self._addRightChild(rightChild)
        
        
    def addChild(self, child):
        self._addLeftChild(child)
        
    def getAllNodes(self):
        leftNodes = []
        rightNodes = []
        
        if self.left != None:
            leftNodes = self.left.getAllNodes()
        if self.right != None:
            rightNodes = self.right.getAllNodes()
        return [self] + leftNodes + rightNodes

    def getAllLabels(self):
        if self.left != None:
            leftLabels = self.left.getAllLabels()
        else:
            leftLabels = []
            
        if self.right != None:
            rightLabels = self.right.getAllLabels()
        else:
            rightLabels = []
        return [self.label] + leftLabels + rightLabels

    def getSize(self):
        size = 1
        if self.left != None:
            size += self.left.getSize()
        if self.right != None:
            size += self.right.getSize()
        return size

    def getDepth(self):
        depth = 0
        if self.left != None:
            depth = max(depth, 1 + self.left.getDepth())
        if self.right != None:
            depth = max(depth, 1 + self.right.getDepth())
        return depth


    def __repr__(self):
        if self.left == None and self.right == None:
            return self.label
        
        # the (not enforced assumption) is that if a node has only one child, that is the left one
        elif self.left != None and self.right == None:
            return self.label + '(' + self.left.__repr__() + ')'
        
        elif self.left != None and self.right != None:
            return self.label + '(' + self.left.__repr__() + ',' + self.right.__repr__() + ')'


class Formula(SimpleTree):
    
    def __init__(self, formulaArg = "dummyF"):
        
        if not isinstance(formulaArg, str):
            self.label = formulaArg[0]
            self.left = formulaArg[1]
            try:
                self.right = formulaArg[2]
            except:
                self.right = None
        else:
            super().__init__(formulaArg)

    def __lt__(self, other):

        if self.getDepth() < other.getDepth():
            return True
        elif self.getDepth() > other.getDepth():
            return False
        else:
            if self._isLeaf() and other._isLeaf():
                return self.label < other.label

            if self.left != other.left:
                return self.left < other.left

            if self.right is None:
                return False
            if other.right is None:
                return True
            if self.right != other.right:
                return self.right < other.right

            else:
                return self.label < other.label

    """
       normalization in an incomplete method to eliminate equivalent formulas
       """

    @classmethod
    def normalize(cls, f):

        if f is None:
            return None
        if f._isLeaf():
            return Formula([f.label, f.left, f.right])
        fLeft = Formula.normalize(f.left)
        fRight = Formula.normalize(f.right)

        if fLeft.label == "true":
            if f.label in ['|', 'F', 'G', 'X']:
                return Formula("true")
            if f.label in ["&", "->"]:
                return Formula.normalize(fRight)
            if f.label == "!":
                return Formula("false")
            if f.label == "U":
                return Formula.normalize(Formula(["F", fRight, None]))

        if fLeft.label == "false":
            if f.label in ['->', '!']:
                return Formula["true"]
            if f.label in ['&', 'F', 'G', 'X']:
                return Formula["false"]
            if f.label in ['|', 'U']:
                return Formula.normalize(fRight)

        if not fRight is None:
            if fRight.label == "true":
                if f.label in ['|', "->", 'U']:
                    return Formula("true")
                if f.label in ["&"]:
                    return Formula.normalize(fLeft)

            if fRight.label == "false":
                if f.label in []:
                    return Formula["true"]
                if f.label in ['&', 'U']:
                    return Formula["false"]
                if f.label in ['|']:
                    return Formula.normalize(fLeft)
                if f.label in ['->']:
                    return Formula.normalize(Formula(["!", fRight, None]))

        # elimiting p&p and similar
        if fLeft == fRight:
            if f.label in ['&', 'U', '|']:
                return Formula.normalize(fLeft)
            else:
                return Formula("true")

        # eliminating Fp U p and !p U p
        if f.label == 'U':
            if fLeft.label == 'F' or fLeft.label == '!':
                fLeftLeft = Formula.normalize(fLeft.left)
                if fLeftLeft == fRight:
                    return Formula.normalize(Formula(['F', fLeftLeft]))
            if fRight.label == 'F':
                fRightLeft = Formula.normalize(fRight.left)
                if fRightLeft == fLeft:
                    return fRight

        if f.label == 'F' and fLeft.label == 'F':
            return fLeft

        # if there is p | q, don't add q | p
        if f.label in symmetric_operators and not fLeft < fRight:
            return Formula([f.label, fRight, fLeft])

        return Formula([f.label, fLeft, fRight])


    @classmethod
    def convertTextToFormula(cls, formulaText):
        
        f = Formula()
        try:
            formula_parser = Lark(r"""
                ?formula: _binary_expression
                        |_unary_expression
                        | constant
                        | variable
                !constant: "true"
                        | "false"
                _binary_expression: binary_operator "(" formula "," formula ")"
                _unary_expression: unary_operator "(" formula ")"
                variable: /x[0-9]*/
                !binary_operator: "&" | "|" | "->" | "U"
                !unary_operator: "F" | "G" | "!" | "X"
                
                %import common.SIGNED_NUMBER
                %import common.WS
                %ignore WS 
             """, start = 'formula')
        
            
            tree = formula_parser.parse(formulaText)
            #print(tree.pretty())
            
        except Exception as e:
            print("can't parse formula %s" %formulaText)
            print("error: %s" %e)
            
        
        f = TreeToFormula().transform(tree)
        return f

    def prettyPrint(self, top=False):
        if top is True:
            lb = ""
            rb = ""
        else:
            lb = "("
            rb = ")"
        if self._isLeaf():
            return self.label
        if self.label in unary_operators:
            return lb + self.label +" "+ self.left.prettyPrint() + rb
        if self.label in binary_operators:
            return lb + self.left.prettyPrint() +" "+  self.label +" "+ self.right.prettyPrint() + rb
    
    
    
    def getAllVariables(self):
        allNodes = list(set(self.getAllNodes()))
        return [ node for node in allNodes if node._isLeaf() == True ]
    
    def getNumberOfSubformulas(self):
        return len(self.getSetOfSubformulas())
    
    def getSetOfSubformulas(self):
        if self.left == None and self.right == None:
            return [repr(self)]
        leftValue = []
        rightValue = []
        if self.left != None:
            leftValue = self.left.getSetOfSubformulas()
        if self.right != None:
            rightValue = self.right.getSetOfSubformulas()
        return list(set([repr(self)] + leftValue + rightValue))
        
             

class TreeToFormula(Transformer):
        def formula(self, formulaArgs):
            
            return Formula(formulaArgs)
        def variable(self, varName):
            return Formula([str(varName[0]), None, None])
        def constant(self, arg):
            if str(arg[0]) == "true":
                connector = "|"
            elif str(arg[0]) == "false":
                connector = "&"
            return Formula([connector, Formula(["x0", None, None]), Formula(["!", Formula(["x0", None, None] ), None])])
                
        def binary_operator(self, args):
            return str(args[0])
        def unary_operator(self, args):
            return str(args[0])
    
        
        
class DecisionTreeFormula(SimpleTree):
    def __repr__(self):
        left_repr = f"{self.left!r}" if self.left!=None else "*"
        right_repr = f"{self.right!r}" if self.right!=None else "*"
        return f"{self.label};{left_repr};{right_repr}"

    def prettyPrint(self, top=False):
        left_repr = self.left.prettyPrint(top) if self.left!=None else "⊤"
        right_repr = self.right.prettyPrint(top) if self.right!=None else "⊥"
        label_repr = self.label.prettyPrint(top) if isinstance(self.label, SimpleTree) else self.label
        return f"{label_repr};{left_repr};{right_repr}"

    def flattenToFormula(self):
        if self.left==None and self.right==None: # no child
            return self.label
        elif self.left==None: # only "False" child
            return Formula(["|", self.label, self.right.flattenToFormula()])
        elif self.right==None: # only "True" child
            return Formula(["&", self.label, self.left.flattenToFormula()])
        else:
            return Formula(["|",
                Formula(["&", self.label, self.left.flattenToFormula()]),
                Formula(["&", Formula(["!", self.label]), self.right.flattenToFormula()]),
            ])

    def trimPseudoNodes(self):
        """return a copy where pseudo leaves such as "..." are trimed"""
        if not isinstance(self.label, Formula):
            return None
        left, right = None, None
        if self.left is not None: left = self.left.trimPseudoNodes()
        if self.right is not None: right = self.right.trimPseudoNodes()
        if left is self.left and right is self.right:
            return self
        result = DecisionTreeFormula(label=self.label)
        result.left, result.right = left, right
        return result

    def writeDotFile(self, file, traces=None):
        if isinstance(file, str): cm = open(file, "w")
        # else: cm = contextlib.nullcontext(file)
        else: cm = contextlib.contextmanager(lambda: (yield file))()
        with cm as stream:
            stream.write('digraph Tree {\n')
            stream.write('\tnode [shape=box, style="filled", color="black"] ;\n')
            DecisionTreeFormula._writeDotNode(self, stream, indent='\t', traces=traces, alltraces=traces)
            stream.write('}\n')

    @staticmethod
    def _writeDotNode(node, stream, name="", indent='', traces=None, alltraces=None):
        if alltraces is None: alltraces = traces
        infos = []
        style = ["filled"]
        fillcolor = "#ffffff"
        formula = None

        if node is None:
            if name.endswith("T"):
                infos.append("⊤")
                fillcolor = "#37a600"
                style.append("dashed")
                formula = Formula('true')
            elif name.endswith("F"):
                infos.append("⊥")
                fillcolor = "#e6300c"
                style.append("dashed")
                formula = Formula('false')
        elif not isinstance(node.label, Formula):
            infos.append(node.label)
            fillcolor = "#9940ec"
        else:
            infos.append(node.label.prettyPrint())
            formula = node.label

        if traces is not None:
            infos.append(f"traces = {len(traces.positive)} + {len(traces.negative)} = {len(traces)}")
            traces_percentage = p = len(traces)/len(alltraces)
            if formula is not None:
                if len(traces):
                    misclassification = m = 1-traces.get_score(formula, score='count')
                    # fillcolor=f"#{int(m*255):02x}{int((1-m)*255):02x}{0:02x}"
                    fillcolor=f"#{int((p*m+1-p)*255):02x}{int((1-p*m)*255):02x}{int((1-p)*255):02x}"
                    infos.append(f"misclass = {misclassification*100:.2f}%")
                else:
                    # fillcolor=f"#{191:02x}{191:02x}{191:02x}"
                    fillcolor=f"#{255:02x}{255:02x}{255:02x}"
            else:
                fillcolor=f"#{int(255-(255-153)*p):02x}{int(255-(255-64)*p):02x}{int(255-(255-236)*p):02x}"
            #TODO: use adequate library for mixing colors

        opts = dict(
            label=r"\n".join(infos),
            style=",".join(style),
            fillcolor=fillcolor,
        )
        opts = ', '.join(f'{k}="{v}"' for k,v in opts.items())
        stream.write(f'{indent}{name or "root"} [{opts}] ;\n')
        if name.endswith("T"):
            stream.write(f'{indent}{name[:-1] or "root"} -> {name} [labeldistance=2.5, labelangle=45, headlabel="True"] ;\n')
        elif name.endswith("F"):
            stream.write(f'{indent}{name[:-1] or "root"} -> {name} [labeldistance=2.5, labelangle=-45, headlabel="False"] ;\n')

        if node is not None and formula is not None:
            accTraces, rejTraces = None, None
            if traces is not None:
                accTraces, rejTraces = traces.splitEval(formula)
            __class__._writeDotNode(node.left,  stream, name=name+"T", indent=indent+"\t", traces=accTraces, alltraces=alltraces)
            __class__._writeDotNode(node.right, stream, name=name+"F", indent=indent+"\t", traces=rejTraces, alltraces=alltraces)
