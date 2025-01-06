from consts import *
from language import DFA, build_dfa

build_dfa()


class EndOfFileException(Exception):
    pass


class Scanner:
    identifiers = []
    dfa = DFA()
    QUIET_ACCEPTS = (TokenType.COMMENT, TokenType.WHITESPACE)

    def __init__(self, input_stream, errors_stream, symbols_stream):
        self.input_stream = input_stream
        self.errors_stream = errors_stream
        self.symbols_stream = symbols_stream
        self.lineno = 1
        self.unclosed_comment_lineno = 0
        self.last_error_lineno = 0
        self.last_token_lineno = 0
        self.current_token_lexeme = ''
        self.symbol_line = 1
        self._input_ended = False
        self._returned_eof = False
        self._input_endline = False
        self.look_ahead = None
        self._token_generator = self._get_next_token()
        for keyword in KEYWORDS:
            self._write_to_symbol_table(keyword)

    def get_next_token(self):

        return next(self._token_generator)

    def _get_next_token(self):
        char = self.read_char()
        state = self.dfa.get_state('start')
        while True:
            state.on_enter(self)
            if state.accept:
                accept_result = self.on_accept(state.accept)
                self.current_token_lexeme = ''
                state = self.dfa.get_state('start')
                if accept_result is not None:
                    yield accept_result[0], accept_result[1]
            elif state.error:
                self.error_handler(state.error)
                self.current_token_lexeme = ''
                state = self.dfa.get_state('start')
                char = self.read_char()
            elif char is None:
                self.current_token_lexeme = ''
                raise EndOfFileException()
            else:
                edge = state.next(char)
                if edge.consume_char:
                    self.current_token_lexeme += char
                    char = self.read_char()
                state = edge.to()

    def read_char(self):
        if self._input_ended:
            return None

        if self._input_endline:
            self.lineno += 1
            self._input_endline = False

        c = self.input_stream.read(1)
        if not c:
            self._input_ended = True
            return '$'

        if c == '\n':
            self._input_endline = True

        return c

    def error_handler(self, error: ScannerErrorType):
        if error == ScannerErrorType.INVALID_INPUT:
            self._write_to_errors(f'({self.current_token_lexeme}, Invalid input) ', self.lineno)
        elif error == ScannerErrorType.UNCLOSED_COMMENT:
            self._write_to_errors(f'({self.current_token_lexeme[:7]}..., Unclosed comment)',
                                  self.unclosed_comment_lineno)
        elif error == ScannerErrorType.UNMATCHED_COMMENT:
            self._write_to_errors(f'(*/, Unmatched comment) ', self.lineno)
        elif error == ScannerErrorType.INVALID_NUMBER:
            self._write_to_errors(f'({self.current_token_lexeme}, Invalid number) ', self.lineno)

    def token_generator(self, token: TokenType):
        return str(token.name), self.current_token_lexeme

    def on_accept(self, token: TokenType):
        if token in self.QUIET_ACCEPTS:
            return None

        if token == TokenType.ID_OR_KEYWORD:
            if self.current_token_lexeme in KEYWORDS:
                return self.token_generator(TokenType.KEYWORD)
            else:
                if self.current_token_lexeme not in self.identifiers:
                    self.identifiers.append(self.current_token_lexeme)
                    self._write_to_symbol_table(self.current_token_lexeme)
                return self.token_generator(TokenType.ID)
        return self.token_generator(token)

    def _write_to_errors(self, error_message, error_line):

        if error_line != self.last_error_lineno:
            if self.last_error_lineno != 0:
                self.errors_stream.write('\n')
            self.errors_stream.write(f'{error_line}. ')
            self.last_error_lineno = error_line
        self.errors_stream.write(error_message)

    def _write_to_symbol_table(self, symbol):
        if self.symbol_line != 1:
            self.symbols_stream.write('\n')
        self.symbols_stream.write(f'{self.symbol_line}. {symbol}')
        self.symbol_line += 1
