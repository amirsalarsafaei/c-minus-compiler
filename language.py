import string
from typing import Iterable, Sequence, Optional, Callable
from consts import *


def do_nothing(*args, **kwargs):
    pass


class DFA:
    _instance: "DFA" = None

    @classmethod
    def get_instance(cls):
        return cls._instance

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DFA, cls).__new__(cls)
            cls._instance.states = {}
        return cls._instance

    def add_state(self, name, state):
        self.states[name] = state

    def get_state(self, name) -> "State":
        return self.states.get(name, None)


class State:
    def __init__(self, edges, on_enter: Callable = do_nothing, accept: Optional[TokenType] = None,
                 error: Optional[ScannerErrorType] = None):
        self.edges = edges
        self.on_enter = on_enter
        self.accept = accept
        self.error = error
        if self.error is not None and self.accept is not None:
            raise Exception('both error and accept cannot be set at the same time')

    def next(self, ch) -> "Edge":
        for edge in self.edges:
            if edge.check(ch):
                return edge
        raise Exception('no edge found')


class Edge:
    def __init__(self, to, alpha, exclusion_alpha=False, consume_char=True):
        self._to = to
        self.alpha = alpha
        self.exclusion_alpha = exclusion_alpha
        self.consume_char = consume_char

    def check(self, ch):
        flag = self._check(ch)
        if self.exclusion_alpha:
            return not flag
        return flag

    def _check(self, ch):
        if isinstance(self.alpha, str):
            if len(self.alpha) == 1:
                return ch == self.alpha
        if isinstance(self.alpha, Iterable) or isinstance(self.alpha, Sequence):
            for i in self.alpha:
                if i == ch:
                    return True
        return False

    def to(self):
        if isinstance(self._to, str):
            return DFA().get_state(self._to)
        return self._to


def build_dfa():
    if DFA.get_instance() is not None:
        return
    dfa = DFA()

    dfa.add_state(
        'start',
        State(edges=[
            Edge(to='num_checker', alpha=string.digits),
            Edge(to='star_checker', alpha='*'),
            Edge(to='id_keyword_checker', alpha=string.ascii_letters),
            Edge(to='equal_checker', alpha='='),
            Edge(to='symbol_checker', alpha=SYMBOLS),
            Edge(to='start_comment_checker', alpha='/'),
            Edge(to='accept_whitespace', alpha=WHITE_SPACES),
            Edge(to='accept_end', alpha=END_OF_FILE),
            Edge(to='invalid_input', alpha='', exclusion_alpha=True)
        ])
    )

    dfa.add_state(
        'num_checker',
        State(
            edges=[
                Edge(to='num_checker', alpha=string.digits),
                Edge(to='accept_num', alpha=string.ascii_letters, exclusion_alpha=True, consume_char=False),
                Edge(to='invalid_num', alpha=string.ascii_letters)
            ]
        )
    )

    dfa.add_state(
        'accept_num',
        State(edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)], accept=TokenType.NUM)
    )

    dfa.add_state(
        'invalid_num',
        State(
            edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
            error=ScannerErrorType.INVALID_NUMBER
        )
    )

    dfa.add_state(
        'star_checker',
        State(edges=[
            Edge(to='unmatched_comment', alpha='/'),
            Edge(to='invalid_input', alpha=VALID_INPUTS, exclusion_alpha=True),
            Edge(to='accept_symbol', alpha='', exclusion_alpha=True, consume_char=False),
        ])
    )

    dfa.add_state(
        'unmatched_comment',
        State(edges=[Edge('start', alpha='', exclusion_alpha=True, consume_char=False)],
              error=ScannerErrorType.UNMATCHED_COMMENT)
    )

    dfa.add_state(
        'id_keyword_checker',
        State(edges=[
            Edge(to='id_keyword_checker', alpha=string.ascii_letters + string.digits),
            Edge(to='invalid_input', alpha=VALID_INPUTS, exclusion_alpha=True),
            Edge(to='accept_id_keyword', alpha=string.ascii_letters + string.digits, exclusion_alpha=True,
                 consume_char=False)
        ])
    )

    dfa.add_state(
        'accept_id_keyword',
        State(edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
              accept=TokenType.ID_OR_KEYWORD)
    )

    dfa.add_state(
        'equal_checker',
        State(edges=[Edge(to='accept_symbol', alpha='='),
                     Edge(to='invalid_input', alpha=VALID_INPUTS, exclusion_alpha=True),
                     Edge(to='accept_symbol', alpha='', exclusion_alpha=True, consume_char=False)])
    )

    dfa.add_state(
        'symbol_checker',
        State(edges=[
                     Edge(to='accept_symbol', alpha='', exclusion_alpha=True, consume_char=False)])
    )

    dfa.add_state(
        'accept_symbol',
        State(edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
              accept=TokenType.SYMBOL)
    )

    dfa.add_state(
        'start_comment_checker',
        State(edges=[Edge(to='started_comment_checker', alpha='*'),
                     Edge(to='invalid_start_comment', alpha='*', exclusion_alpha=True)])
    )

    dfa.add_state(
        'invalid_start_comment',
        State(edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
              error=ScannerErrorType.INVALID_INPUT)
    )

    def started_comment_on_enter(scanner):
        scanner.unclosed_comment_lineno = scanner.lineno
        return

    dfa.add_state(
        'started_comment_checker',
        State(
            edges=[
                Edge(to='in_comment_checker', alpha='', exclusion_alpha=True, consume_char=False)
            ],
            on_enter=started_comment_on_enter
        )
    )

    dfa.add_state(
        'in_comment_checker',
        State(
            edges=[
                Edge(to='end_comment_checker', alpha='*'),
                Edge(to='in_comment_checker', alpha='*', exclusion_alpha=True)
            ],
        )
    )

    dfa.add_state(
        'end_comment_checker',
        State(
            edges=[
                Edge(to='ended_comment_checker', alpha='/'),
                Edge(to='in_comment_checker', alpha='/', exclusion_alpha=True, consume_char=True)
            ]
        )
    )

    def ended_comment_on_enter(scanner):
        scanner.unclosed_comment_lineno = 0

    dfa.add_state(
        'ended_comment_checker',
        State(
            edges=[
                Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)
            ],
            on_enter=ended_comment_on_enter,
            accept=TokenType.COMMENT
        )
    )

    dfa.add_state(
        'accept_whitespace',
        State(
            edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
            accept=TokenType.WHITESPACE
        )
    )

    dfa.add_state(
        'accept_end',
        State(
            edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
            accept=TokenType.END_OF_FILE
        )
    )

    dfa.add_state(
        'invalid_input',
        State(
            edges=[Edge(to='start', alpha='', exclusion_alpha=True, consume_char=False)],
            error=ScannerErrorType.INVALID_INPUT,
        )
    )
