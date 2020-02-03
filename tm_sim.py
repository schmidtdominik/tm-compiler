# computing functions using a deterministic turing machine
import string
import itertools
from typing import List, Set, Dict, Tuple
from collections import deque

#j = itertools.chain.from_iterable(itertools.combinations_with_replacement(string.ascii_lowercase, r=i) for i in itertools.count())
#j = (''.join(k) for k in j)

class TuringMachine:
    def __init__(self, transitions: Dict[Tuple, Tuple[str, List[int], List[int]]], initial_state: str, states: List[str], tapes: List[str]):
        self.symbols = [0, 1, -1]
        self.transitions = transitions
        self.initial_state = initial_state
        self.states = states
        self.tape_names = tapes
        assert self.initial_state in self.states
        assert all(q[0] in states for q in transitions.keys()) and all(q[0] in states for q in transitions.values())

    def run(self, initial_tape_contents=None, debugger=False):
        if initial_tape_contents is None:
            initial_tape_contents = {}
        self.tapes = [Tape(n, initial_tape_contents[n]) if n in initial_tape_contents else Tape(n) for n in self.tape_names]
        self.current_state = self.initial_state

        for step in itertools.count():
            if debugger:
                for tape in self.tapes:
                    print('DEBUGGER: ', tape.name, tape.interpreted_value, tape.value)
            k = (self.current_state, *[tape.read() for tape in self.tapes])
            if k in self.transitions:
                r = self.transitions[k]
                if debugger:
                    print('\nDEBUGGER:', k, '→', r)
                self.current_state = r[0]
                for i, val, dir in zip(itertools.count(), r[1], r[2]):
                    self.tapes[i].write_and_move(val, dir)
            else:
                print(f'TM halted after {step} step.')
                for tape in self.tapes:
                    print(tape.name, tape.interpreted_value, tape.value)
                return

class Tape:
    def __init__(self, name: str, initial_tape_contents: int = None):
        self.name = name
        self.value = deque([-1]) if initial_tape_contents is None else deque([int(c) for c in bin(initial_tape_contents)[2:][::-1]])
        self.pointer = 0

    def read(self):
        return self.value[self.pointer]

    def write_and_move(self, value: int, direction: int):
        assert value in [0, 1, -1]
        self.value[self.pointer] = value

        if direction == -1:
            if self.pointer == 0:
                self.value.appendleft(-1)
            else:
                self.pointer -= 1
        elif direction == 1:
            if self.pointer+1 == len(self.value):
                self.value.append(-1)
                self.pointer += 1
            else:
                self.pointer += 1

    @property
    def interpreted_value(self):
        trimmed = ''.join([str(v) for v in self.value]).replace('-1', ' ').strip()
        if ' ' in trimmed or not trimmed:
            return f'>>{trimmed.replace(" ", "(-1)")}<<'
        else:
            return int('0b' + trimmed[::-1], 2)


# tm that copies from tape 'a' to tape 'b'
tm_transitions = {
    ('0', 0, 0): ('0', [0, 0], [1, 1]),
    ('0', 0, 1): ('0', [0, 0], [1, 1]),
    ('0', 0, -1): ('0', [0, 0], [1, 1]),

    ('0', 1, 0): ('0', [1, 1], [1, 1]),
    ('0', 1, 1): ('0', [1, 1], [1, 1]),
    ('0', 1, -1): ('0', [1, 1], [1, 1]),

    ('0', -1, 0): ('1', [-1, -1], [1, 1]),
    ('0', -1, 1): ('1', [-1, -1], [1, 1]),
    ('0', -1, -1): ('1', [-1, -1], [1, 1]),
}
tm = TuringMachine(transitions=tm_transitions, initial_state='q', states=['0', '1'], tapes=['a', 'b'])
tm.run(initial_tape_contents={'a': 15}, debugger=True)