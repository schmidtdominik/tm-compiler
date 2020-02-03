from typing import List, Union, Dict, Tuple

from numpy import product

""" code to turing machine compilation process:
↓ 1. Program definition
↓ 2. Declare TM I/O variables and compilation options (skip step 5&6?)
↓ 3. Program atomization
[Sample testing possible]
↓ 4. Compute access graph (def-use/use-def chains)
↓ 5. Constant folding & propagation, dead store & code elimination (+ loop & conditional optimization)
[Sample testing]
↓ 6. Compile to TM
[Sample testing]
↓ 7. Profile TM
↓ (8. convert multi-tape tm to single-tape tm)

TODO:

- randomized tests
- optimize commutative ops during constant folding (convert to aggregate ops first)
    a <= (a+1)+2
    a <= (a*2)*3

"""

def indent(s):
    return '\n'.join(['\t'+k for k in s.splitlines()])

class RecursiveAtomizer:

    def __init__(self, free_vars: set):
        self.free_vars = free_vars
        self.count = 0

    def get_or_create_variable(self):
        if self.free_vars:
            return self.free_vars.pop()
        else:
            v = Var(f'_tmp{self.count}', interstep_var=True)
            self.count += 1
            return v

    def run(self, op: 'Op', target_variable=None):
        instructions = []

        compute_values = []
        if issubclass(type(op), UnaryOp):
            compute_values = [op.a]
        elif issubclass(type(op), BinaryOp):
            compute_values = [op.a, op.b]
        else:
            raise NotImplementedError()

        recollect_tmps = set()
        computed_values = []

        for v in compute_values:
            if type(v) is int:
                tmp = self.get_or_create_variable()
                instructions.append(Write(tmp, v))
                computed_values.append(tmp)
                recollect_tmps.add(tmp)
            elif type(v) is Var:
                computed_values.append(v)
            elif issubclass(type(v), Op):
                rec_instructions, tmp = self.run(v)
                instructions.extend(rec_instructions)
                computed_values.append(tmp)
                recollect_tmps.add(tmp)
            else:
                raise NotImplementedError()

        if target_variable is None:
            target_variable = self.get_or_create_variable()

        if issubclass(type(op), UnaryOp):
            instructions.append(Assign(target_variable, type(op)(computed_values[0])))
        elif issubclass(type(op), BinaryOp):
            instructions.append(Assign(target_variable, type(op)(*computed_values[:2])))
        else:
            raise NotImplementedError()

        self.free_vars.update(recollect_tmps)

        return instructions, target_variable

class ContainsVariables(object):
    @property
    def variables(self):
        return None

class Instruction(ContainsVariables):
    @property
    def variables(self) -> List['Var']:
        pass

    def execute(self, variable_assignments: Dict['Var', int]) -> Dict['Var', int]:
        pass

class Value(ContainsVariables):
    # values are instructions because they also have variables() methods

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        pass

    @staticmethod
    def evaluate_or_int(v: Union['Value', int], variable_assignments: Dict['Var', int]) -> int:
        if type(v) is int:
            return v
        else:
            return v.evaluate(variable_assignments)

    def __eq__(self, other) -> 'Op':
        return Equals(self, other)

    def __ne__(self, other) -> 'Op':
        return Not(Equals(self, other))

    def __lt__(self, other) -> 'Op':
        return Less(self, other)

    def __gt__(self, other) -> 'Op':
        return Greater(self, other)

    def __invert__(self) -> 'Op':
        return Not(self)

    def __neg__(self) -> 'Op':
        return Negate(self)

    def __pos__(self) -> 'Value':
        return self

    def __add__(self, other) -> 'Op':
        return Add(self, other)

    def __sub__(self, other) -> 'Op':
        return Sub(self, other)

    def __mul__(self, other) -> 'Op':
        return Mult(self, other)

    def __floordiv__(self, other) -> 'Op':
        return Div(self, other)

    def __and__(self, other) -> 'Op':
        return And(self, other)

    def __or__(self, other) -> 'Op':
        return Or(self, other)

    def __radd__(self, other) -> 'Op':
        return Add(other, self)

    def __rsub__(self, other) -> 'Op':
        return Sub(other, self)

    def __rmul__(self, other) -> 'Op':
        return Mult(other, self)

    def __rfloordiv__(self, other) -> 'Op':
        return Div(other, self)

    def __rand__(self, other) -> 'Op':
        return And(other, self)

    def __ror__(self, other) -> 'Op':
        return Or(other, self)

class Op(Value):
    symbol = None

class Assign(Instruction):
    def __init__(self, variable: 'Var', value: Union['Value', int]):
        self.value = value
        self.variable = variable

    def __repr__(self):
        return f'{repr(self.variable)} = {repr(self.value)}'

    @property
    def variables(self):
        return [self.variable] + ([self.value] if type(self.value) is Var else [])

    def execute(self, variable_assignments):
        variable_assignments[self.variable] = Value.evaluate_or_int(self.value, variable_assignments)
        return variable_assignments

class Copy(Instruction):
    def __init__(self, a: 'Var', b: 'Var'):
        self.a = a
        self.b = b

    def __repr__(self):
        return f'{repr(self.a)} <=cp {repr(self.b)}'

    @property
    def variables(self):
        return [self.a, self.b]

    def execute(self, variable_assignments):
        variable_assignments[self.a] = variable_assignments[self.b]
        return variable_assignments

class Write(Instruction):
    def __init__(self, a: 'Var', b: int):
        self.a = a
        self.b = b

    def __repr__(self):
        return f'{repr(self.a)} := {repr(self.b)}'

    @property
    def variables(self):
        return [self.a]

    def execute(self, variable_assignments):
        variable_assignments[self.a] = self.b
        return variable_assignments

class While(Instruction):
    def __init__(self, condition: Union['Value', int], body: 'Program'):
        self.condition = condition
        self.body = body

    def execute(self, variable_assignments: Dict['Var', int]) -> Dict['Var', int]:
        while bool(Value.evaluate_or_int(self.condition, variable_assignments)):
            variable_assignments = self.body.execute(variable_assignments)
        return variable_assignments

    def __repr__(self):
        return f'while {repr(self.condition)}:\n{indent(repr(self.body))}'

    @property
    def variables(self):
        return self.body.variables + (self.condition.variables if type(self.condition) is not int else [])

class If(Instruction):
    def __init__(self, condition: Union['Value', int], body_if: 'Program', body_else: 'Program'):
        self.condition = condition
        self.body_if = body_if
        self.body_else = body_else

    def __repr__(self):
        return f'if {repr(self.condition)}:\n{indent(repr(self.body_if))}\nelse\n{indent(repr(self.body_else))}'

    @property
    def variables(self):
        return self.body_if.variables + self.body_else.variables + (self.condition.variables if type(self.condition) is not int else [])

    def execute(self, variable_assignments: Dict['Var', int]) -> Dict['Var', int]:
        if bool(Value.evaluate_or_int(self.condition, variable_assignments)):
            return self.body_if.execute(variable_assignments)
        else:
            return self.body_else.execute(variable_assignments)

class UnaryOp(Op):

    def __init__(self, a: Union['Value', int]):
        # a is either a variable, Op result or integer
        self.a = a

    @property
    def variables(self):
        return [self.a] if type(self.a) is Var else []

    def __repr__(self):
        return f'({self.symbol}{repr(self.a)})'

class BinaryOp(Op):
    def __init__(self, a: Union['Value', int], b: Union['Value', int]):
        # a and b are either variable names, Op results or integers
        self.a = a
        self.b = b

    def __repr__(self):
        return f'({repr(self.a)} {self.symbol} {repr(self.b)})'

    @property
    def variables(self):
        return [k for k in [self.a, self.b] if type(k) is Var]

class AggregateOp(Op):

    def __init__(self, a: List[Union['Value', int]]):
        self.a = a

    def __repr__(self):
        s = f' {self.symbol} '.join([repr(k) for k in self.a])
        return f'({s})'

class Add(BinaryOp):
    symbol = '+'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return self.evaluate_or_int(self.a, variable_assignments) + self.evaluate_or_int(self.b, variable_assignments)

class Sub(BinaryOp):
    symbol = '-'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return self.evaluate_or_int(self.a, variable_assignments) - self.evaluate_or_int(self.b, variable_assignments)

class Mult(BinaryOp):
    symbol = '*'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return self.evaluate_or_int(self.a, variable_assignments) * self.evaluate_or_int(self.b, variable_assignments)

class Div(BinaryOp):
    symbol = '//'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return self.evaluate_or_int(self.a, variable_assignments) // self.evaluate_or_int(self.b, variable_assignments)

class And(BinaryOp):
    # Logical And
    symbol = '&'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return bool(self.evaluate_or_int(self.a, variable_assignments)) and bool(self.evaluate_or_int(self.b, variable_assignments))

class Or(BinaryOp):
    # Logical Or
    symbol = '|'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return bool(self.evaluate_or_int(self.a, variable_assignments)) or bool(self.evaluate_or_int(self.b, variable_assignments))

class Less(BinaryOp):
    symbol = '<'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return int(self.evaluate_or_int(self.a, variable_assignments) < self.evaluate_or_int(self.b, variable_assignments))

class Equals(BinaryOp):
    symbol = '=='

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return int(self.evaluate_or_int(self.a, variable_assignments) == self.evaluate_or_int(self.b, variable_assignments))

class Greater(BinaryOp):
    symbol = '>'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return int(self.evaluate_or_int(self.a, variable_assignments) > self.evaluate_or_int(self.b, variable_assignments))

class Not(UnaryOp):
    # Logical Not
    symbol = '~'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return int(not (bool(self.evaluate_or_int(self.a, variable_assignments))))

class Negate(UnaryOp):
    symbol = '-'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return -self.evaluate_or_int(self.a, variable_assignments)

class Sum(AggregateOp):
    symbol = '+'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return sum([self.evaluate_or_int(j, variable_assignments) for j in self.a])

class Product(AggregateOp):
    symbol = '*'

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return int(product([self.evaluate_or_int(j, variable_assignments) for j in self.a]))

class Var(Value):

    def __init__(self, name, interstep_var=False):
        self.name = name
        self.interstep_var = interstep_var

    def __repr__(self):
        return f'{self.name}'

    def __hash__(self):
        return hash(self.name) # hash((self.name, id(self))) <-- don't do this

    @property
    def variables(self):
        return [self]

    def assign(self, v):
        return Assign(self, v)

    def __iadd__(self, other):
        return Assign(self, self + other)

    def __isub__(self, other):
        return Assign(self, self - other)

    def __imul__(self, other):
        return Assign(self, self * other)

    def __ifloordiv__(self, other):
        return Assign(self, self // other)

    def __iand__(self, other):
        return Assign(self, self & other)

    def __ior__(self, other):
        return Assign(self, self | other)

    def __ilshift__(self, other): # not usable
        return Assign(self, other)

    def __le__(self, other):
        return Assign(self, other)

    def evaluate(self, variable_assignments: Dict['Var', int]) -> int:
        return variable_assignments[self]


class Program(ContainsVariables):
    def __init__(self, p: 'List[Instruction]'):
        self.p = p
        self.tmp_vars = []

    def __repr__(self):
        return '\n'.join([repr(i) for i in self.p])

    @property
    def variables(self):
        return list(set([j for instr in self.p for j in instr.variables]))

    @property
    def interstep_vars(self):
        return {v for v in self.variables if v.interstep_var}

    def execute(self, variable_assignments: Dict['Var', int], debugger: bool = False) -> Dict['Var', int]:
        for j, instr in enumerate(self.p):
            variable_assignments = instr.execute(variable_assignments)
            if debugger:
                print(f'DEBUG: {variable_assignments} \t[VA after line {j+1}]')
        return variable_assignments  # return all variables, not just the output ones, required for Ifs, While's

    @staticmethod
    def create_random():
        pass

    @property
    def as_atomized(self):
        """ Cases where atomization is required

        - 1. Assign('a', 'b') --> Copy('a', 'b')
        - 2. Assign('a', 0) --> Write('a', 0)
        - 3. Assign('a', Op_1(Op_2('x', 'y'), Op_3('z', 'w'))) -->
            Assign('tmp1', Op_2('x', 'y'))
            Assign('tmp2', Op_3('z', 'w'))
            Assign('a', Op_1('tmp1', 'tmp2'))

        - 4. If(Op(..), Program([..]), Program([..])) -->
            Assign('tmp1', Op(..))
            If('tmp1', Program([..]), Program([..]))

        - 5. While(Op(..), Program([..])) -->
            Assign('tmp1', Op(..))
            While('tmp1', Program([.., Assign('tmp1', Op(..))]))

        Order: (4 , 5) -> 3 -> (1, 2)

        """

        prog = self.p

        tmp1 = Var('_tmpX', interstep_var=True)

        if not len(set(self.variables + [tmp1])) == len(set(self.variables)) + 1:
            raise RuntimeError('The program cannot contain a variable named _tmp1_')

        # 4.
        new_p = []
        for k in prog:
            if type(k) is If and type(k.condition) is not Var:
                new_p.append(Assign(tmp1, k.condition))
                new_p.append(If(tmp1, k.body_if.as_atomized, k.body_else.as_atomized))
            elif type(k) is If:
                new_p.append(If(k.condition, k.body_if.as_atomized, k.body_else.as_atomized))
            else:
                new_p.append(k)
        prog = new_p

        # 5.
        new_p = []
        for k in prog:
            if type(k) is While and type(k.condition) is not Var:
                new_p.append(Assign(tmp1, k.condition))
                new_p.append(While(tmp1, Program(k.body.as_atomized.p + [Assign(tmp1, k.condition)])))
            elif type(k) is While:
                new_p.append(While(k.condition, Program(k.body.as_atomized.p + [Assign(tmp1, k.condition)])))
            else:
                new_p.append(k)
        prog = new_p

        # 3.
        r = RecursiveAtomizer(Program(prog).interstep_vars)

        new_p = []
        for k in prog:
            if type(k) is Assign and issubclass(type(k.value), Op):
                instructions, result_var = r.run(k.value, target_variable=k.variable)
                new_p.extend(instructions)
            else:
                new_p.append(k)
        prog = new_p

        # 1. / 2.
        for i, k in enumerate(prog):
            if type(k) is Assign and type(k.value) is Var and type(k.variable) is str:
                prog[i] = Copy(k.variable, k.value)  # 1.
            elif type(k) is Assign and type(k.value) is int and type(k.variable) is Var:
                prog[i] = Write(k.variable, k.value)  # 2.

        return Program(prog)