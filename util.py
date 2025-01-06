from typing import List, Optional

from consts import AddressType, SymbolDataType, SymbolType


class SymbolTableItem:
    def __init__(
            self,
            scope: int,
            lexeme: Optional[str] = None,
            symbol_type: SymbolType = None,
            size=0,
            data_type: Optional[SymbolDataType] = None,
            is_param=False,
            address=None,
    ):
        self.lexeme = lexeme
        self.symbol_type = symbol_type
        self.scope = scope
        self.size = size
        self.data_type = data_type
        self.address: Address = address
        self.is_param = is_param


class SymbolTable:
    def __init__(self) -> None:
        self.items: List[SymbolTableItem] = []

    def append(self, item: SymbolTableItem):
        self.items.append(item)

    def pop(self):
        self.items.pop()

    def get_last_by_lexeme(self, lexeme) -> Optional[SymbolTableItem]:
        items = list(filter(lambda x: x.lexeme == lexeme, self.items))
        if len(items) == 0:
            return None
        return items[-1]

    def get_scope_symbols(self, scope) -> List[SymbolTableItem]:
        return list(filter(lambda x: x.scope >= scope, self.items))

    def pop_last_scope(self, scope):
        while len(self.items) != 0 and self.items[-1].scope == scope:
            self.items.pop()


class FunctionDetails:
    def __init__(
            self,
            name: str,
            data_type: SymbolDataType,
            pb_idx,
            scope,
            return_address=None,
            return_value_address=None,
            args=None,
    ):
        self.name = name
        self.data_type = data_type
        self.pb_idx = pb_idx
        if args is None:
            self.args: List[ArgDetails] = []
        else:
            self.args = args
        self.return_address = return_address
        self.return_value_address = return_value_address
        self.scope = scope


class LoopDetails:
    def __init__(self, label_pb_idx, lineno, next_pb_idx=None, iterator_expression_pb=None):
        self.label_pb_idx = label_pb_idx
        self.next_pb_idx = next_pb_idx
        if iterator_expression_pb is not None:
            self.iterator_expression_pb = iterator_expression_pb
        else:
            self.iterator_expression_pb = []
        self.breaks_pb_idx = []
        self.condition_jp_pb_idx = 0
        self.lineno = lineno


class Address:
    def __init__(self, address: str, address_type: AddressType):
        self.address = address
        self.address_type = address_type


class Code:
    def __init__(self, op, a, b=None, c=None):
        self.op = op
        self.a = a
        self.b = b
        self.c = c

    def __str__(self) -> str:
        return f"({self.op}, {self.a}, {self._helper_str(self.b)}, {self._helper_str(self.c)})"

    @staticmethod
    def _helper_str(a):
        if a is None:
            return ""
        return a


class IfDetails:
    def __init__(self, condition_jpf_pb_idx, else_jp_pb_idx=None):
        self.condition_jpf_pb_idx = condition_jpf_pb_idx
        self.else_jp_pb_idx = else_jp_pb_idx


class FunctionCallDetails:
    def __init__(self, function: FunctionDetails, args=None):
        self.function = function
        if args is None:
            self.args = []
        else:
            self.args = args


class ArgDetails:
    def __init__(self, name: str, arg_type: SymbolType, address: Address):
        self.name = name
        self.arg_type = arg_type
        self.address = address


class SemanticError:
    def __init__(self, lineno: int, error: str):
        self.lineno = lineno
        self.error = error

    def __str__(self):
        return f"#{self.lineno} : Semantic Error! {self.error}."
