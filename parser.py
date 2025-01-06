from typing import List

from anytree import Node, RenderTree

from codegen import CodeGenerator
from consts import ParserErrorType, TokenType
from scanner import EndOfFileException, Scanner


class Parser:

    def __init__(
        self,
        scanner: Scanner,
        code_gen: CodeGenerator,
        grammar: dict,
        errors_stream,
        parse_tree_stream,
    ) -> None:
        self.scanner = scanner
        self.syncs = grammar.get("follows")
        self.table = grammar.get("table")
        self.non_terminals = set(grammar.get("non_terminals"))
        self.root = Node("Program")
        self.end_node = Node("$")
        self.stack: List[Node] = [self.end_node, self.root]
        self.token = None
        self.token_id = None
        self.token_type = None
        self._eof_missing = False
        self.errors_stream = errors_stream
        self.last_error_lineno = 0
        self.parse_tree_stream = parse_tree_stream
        self.code_gen = code_gen

    def parse(self):
        self._read_from_scanner()
        while len(self.stack) > 0:
            stack_top = self.stack[-1].name
            if stack_top.startswith("#"):
                self.code_gen(stack_top[1:], self._token_pack)
                self.stack.pop()
            else:
                if stack_top not in self.non_terminals:
                    if stack_top != self.token:
                        self.error_handler(error_type=ParserErrorType.TOKEN_MISMATCH)
                    else:
                        self.stack[-1].name = self._sanitize_terminal_name(
                            self.token_type, self.token_id
                        )
                        self.stack.pop()
                        self._read_from_scanner()
                else:
                    rule = self.table.get(stack_top, {}).get(self.token, None)
                    if rule is not None:
                        extend_list = []
                        for i in rule:
                            if i is not None:
                                extend_list.append(Node(i, self.stack[-1]))
                            else:
                                Node("epsilon", self.stack[-1])
                        self.stack.pop()
                        self.stack.extend(list(reversed(extend_list)))
                    else:
                        if self.token in self.syncs[stack_top]:
                            self.error_handler(ParserErrorType.MISSING_NON_TERMINAL)
                        else:
                            self.error_handler(ParserErrorType.ILLEGAL_TOKEN)
        self._after_parse()

    def error_handler(self, error_type: ParserErrorType):
        if error_type == ParserErrorType.ILLEGAL_TOKEN:
            if self.token != "$":
                self._write_to_errors(f"illegal {self.token}", self.scanner.lineno)
            self._read_from_scanner()
        elif error_type == ParserErrorType.TOKEN_MISMATCH:
            if self.stack[-1].name != "$":
                self._write_to_errors(
                    f"missing {self.stack[-1].name}", self.scanner.lineno
                )
            t = self.stack.pop()
            if t.parent is not None:
                t.parent.children = [i for i in t.parent.children if i != t]
        elif error_type == ParserErrorType.MISSING_NON_TERMINAL:
            self._write_to_errors(
                f"missing {self._sanitize_non_terminal_name(self.stack[-1].name)}",
                self.scanner.lineno,
            )
            nt = self.stack.pop()
            if nt.parent is not None:
                nt.parent.children = [i for i in nt.parent.children if i != nt]
        elif error_type == ParserErrorType.UNEXPECTED_EOF:
            self._write_to_errors(f"Unexpected EOF", self.scanner.lineno)
            self._eof_missing = True
            for nt in self.stack:
                if nt.parent is not None:
                    nt.parent.children = [i for i in nt.parent.children if i != nt]
            self.token_id = self.token_type = self.token = None
            self.stack = []

    def _read_from_scanner(self):
        if len(self.stack) == 0:
            return
        try:
            self.token_type, self.token_id = self.scanner.get_next_token()
        except EndOfFileException:
            self.error_handler(error_type=ParserErrorType.UNEXPECTED_EOF)
        self.token = self._sanitize_token_def(
            token_type=self.token_type, token_id=self.token_id
        )
        self._token_pack = (self.token_type, self.token_id)

    def _after_parse(self):
        if not self._eof_missing:
            self.root.children = list(self.root.children) + [self.end_node]
        first = True
        for pre, fill, node in RenderTree(self.root):
            if first:
                first = False
            else:
                self.parse_tree_stream.write("\n")
            self.parse_tree_stream.write(
                "%s%s" % (pre, self._sanitize_non_terminal_name(node.name))
            )
        if self.last_error_lineno == 0:
            self.errors_stream.write("There is no syntax error.")

    def _write_to_errors(self, error_message, error_line):
        if self.last_error_lineno != 0:
            self.errors_stream.write("\n")
        self.errors_stream.write(f"#{error_line} : syntax error, {error_message}")
        self.last_error_lineno = error_line

    @staticmethod
    def _sanitize_non_terminal_name(name: str) -> str:
        return name.replace("_", "-")

    @staticmethod
    def _sanitize_terminal_name(token_type, token_id) -> str:
        if token_type == TokenType.END_OF_FILE.name:
            return "$"
        return f"({token_type}, {token_id})"

    @staticmethod
    def _sanitize_token_def(token_type, token_id) -> str:
        if token_type == TokenType.ID.name or token_type == TokenType.NUM.name:
            return token_type
        return token_id
