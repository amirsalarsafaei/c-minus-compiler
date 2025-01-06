from collections import deque
from io import TextIOWrapper
from symtable import Symbol
from typing import Dict, List, Optional, Tuple

from consts import AddressType, SemanticErrorType, SymbolDataType, SymbolType
from util import (
    Address,
    ArgDetails,
    Code,
    FunctionCallDetails,
    FunctionDetails,
    IfDetails,
    LoopDetails,
    SymbolTable,
    SymbolTableItem, SemanticError,
)


class CodeGenerator:
    INT_SIZE = 4
    STACK_POINTER_ADDRESS = Address(address="0", address_type=AddressType.IMMEDIATE)
    STACK_ADDRESS = Address(address="0", address_type=AddressType.INDIRECT)

    def __init__(self, pb_stream: TextIOWrapper, error_stream: TextIOWrapper, scanner):
        self.scanner = scanner
        self._pb_stream = pb_stream
        self._error_stream = error_stream
        self.symbol_table = SymbolTable()
        self.stack = deque()
        self.semantic_stack = deque()
        self.func_stack = deque()
        self.func_call_stack = deque()
        self.if_stack = deque()
        self.temp = 500
        self.declaration: SymbolTableItem = None
        self.scope = 0
        self.func: FunctionDetails = None
        self.func_map: Dict[str, FunctionDetails] = {}
        self.pb = []
        self.loop_stack: List[LoopDetails] = []
        self.last_variable = ""
        self.last_operator = ""
        self.iterator_expression_mode = False
        self.arith_operator_stack = []
        self._has_error = False
        self._running_iterator_expression = False
        self._iterator_expression_lineno = 0
        self._semantic_errors = []

    def __call__(self, action_symbol: str, token):
        if self.iterator_expression_mode and action_symbol != "end_iterator_expression_mode":
            self.loop_stack[-1].iterator_expression_pb.append((action_symbol, token))
            return
        if action_symbol.startswith("check"):
            getattr(self, action_symbol)(token)
        else:
            getattr(self, action_symbol)(token)

    def start_program(self, _):
        self.pb.append(
            self._create_assign_code(
                Address(str(self.INT_SIZE), AddressType.CONST),
                Address("0", AddressType.IMMEDIATE),
            )
        )
        self.pb.append(
            self._create_jp_code(
                Address("", AddressType.UNKNOWN)
            )
        )
        f_details = FunctionDetails(
            name="output",
            data_type=SymbolDataType.VOID,
            pb_idx=-1,
            scope=self.scope,
            return_address=Address("", AddressType.UNKNOWN),
            args=[
                ArgDetails(
                    name="",
                    arg_type=SymbolType.VARIABLE,
                    address=Address("", AddressType.UNKNOWN)
                )
            ]
        )
        self.symbol_table.append(
            SymbolTableItem(
                scope=0,
                lexeme="output",
                symbol_type=SymbolType.FUNCTION,
                data_type=SymbolDataType.VOID,
                address=Address("", AddressType.UNKNOWN)
            )
        )
        self.func_map[f_details.name] = f_details

    def end_program(self, _):
        if not self._has_error:
            main_func = self.func_map["main"]
            self.pb[1].a = self._jump_address_str(
                Address(str(main_func.pb_idx), AddressType.CONST)
            )
            for i, p in enumerate(self.pb):
                self._pb_stream.write(f"{i}\t{str(p)}\n")
            self._error_stream.write("The input program is semantically correct")
        else:
            self._pb_stream.write("The code has not been generated.")
            semantic_errors_sorted = sorted(self._semantic_errors, key=lambda x: x.lineno)
            for err in semantic_errors_sorted:
                self._error_stream.write(f"{err}\n")

    def start_declaration(self, token):
        self.declaration = SymbolTableItem(scope=self.scope)

    def declaration_type(self, token):
        if token[1].upper() not in SymbolDataType._member_names_:
            return
        self.declaration.data_type = SymbolDataType._member_map_[token[1].upper()]

    def declaration_id(self, token):
        self.check_redeclaration(token)
        self.declaration.lexeme = token[1]

    def declare_function(self, token):
        self.declaration.symbol_type = SymbolType.FUNCTION
        self.declaration.address = Address(str(len(self.pb)), AddressType.CONST)

    def declare_var(self, token):
        self.declaration.symbol_type = SymbolType.VARIABLE
        if self.declaration.data_type == SymbolDataType.VOID:
            self._handle_semantic_error(SemanticErrorType.VOID_TYPE, details={"ID": self.declaration.lexeme})
        self.declaration.address = self._get_temp()
        self._add_code(
            self._create_assign_code(
                Address("0", AddressType.CONST),
                self.declaration.address
            )
        )

    def declare_array(self, token):
        self.declaration.symbol_type = SymbolType.ARRAY
        self.declaration.address.address_type = AddressType.CONST

    def assign_var(self, _):
        pass

    def declare_array_length(self, token):
        self.declaration.size = int(token[1])
        self._reserve_for_array(int(token[1]))

    def end_var_declaration(self, token):
        self.symbol_table.append(self.declaration)
        self.declaration = None

    def start_function_declaration(self, token):
        self.symbol_table.append(self.declaration)
        return_address = self._get_temp()
        return_value_address = self._get_temp()
        self.func = FunctionDetails(
            self.declaration.lexeme,
            self.declaration.data_type,
            len(self.pb),
            self.scope + 1,
            return_value_address=return_value_address,
            return_address=return_address,
        )
        self.func_stack.append(self.func)
        self.func_map[self.declaration.lexeme] = self.func

    def param_id(self, token):
        self.declaration = SymbolTableItem(
            scope=self.scope,
            lexeme=token[1],
            data_type=SymbolDataType.INT,
            symbol_type=SymbolType.VARIABLE,
            address=self._get_temp(),
            is_param=True,
        )
        self.func.args.append(
            ArgDetails(
                name=token[1], arg_type=SymbolType.VARIABLE, address=self.declaration.address,
            )
        )

    def jp_ra(self, _):
        self._add_code(
            self._create_jp_code(
                self.func_stack[-1].return_address
            )
        )

    def param_is_array(self, token):
        self.declaration.symbol_type = SymbolType.ARRAY
        self.func.args[-1].arg_type = SymbolType.ARRAY

    def declared_param(self, token):
        self.declaration.is_param = True
        self.declaration.symbol_type = SymbolType.VARIABLE
        self.declaration.address = self._get_temp()
        self.func.args.append(
            ArgDetails(
                name=self.declaration.lexeme,
                arg_type=SymbolType.VARIABLE,
                address=self.declaration.address,
            )
        )

    def end_param(self, token):
        self.symbol_table.append(self.declaration)
        self.declaration = None

    def start_scope(self, token):
        self.scope += 1

    def end_scope(self, token):
        self.symbol_table.pop_last_scope(self.scope)
        self.scope -= 1

    def start_params_declaration(self, token):
        pass

    def end_params_declaration(self, token):
        pass

    def end_function_declaration(self, token):
        func_details: FunctionDetails = self.func_stack.pop()
        if func_details.name != "main":
            self._add_code(
                self._create_jp_code(
                    func_details.return_address,
                )
            )

    def break_loop(self, token):
        if len(self.loop_stack) == 0:
            self._handle_semantic_error(SemanticErrorType.BREAK, {})
            return
        self.loop_stack[-1].breaks_pb_idx.append(len(self.pb))
        self.pb.append(None)

    def push_address(self, token):
        self.last_variable = token[1]
        symbol = self._get_symbol(token[1])
        if symbol is None:
            self._has_error = True
            self._handle_semantic_error(SemanticErrorType.SCOPING, details={"ID": token[1]})
            symbol = self.__dummy_symbol()
        address = symbol.address
        self._push_stack(address, symbol.symbol_type)

    def push_const(self, token):
        self._push_stack(Address(token[1], AddressType.CONST), SymbolType.VARIABLE)

    def array_index(self, token):
        idx, idx_type = self._pop_stack()
        ar_address, _ = self._pop_stack()
        mul_tmp = self._get_temp()
        self._add_code(
            self._create_mult_code(
                idx, Address(str(self.INT_SIZE), AddressType.CONST), mul_tmp
            )
        )
        self._add_code(self._create_add_code(ar_address, mul_tmp, mul_tmp))
        mul_tmp.address_type = AddressType.INDIRECT
        self._push_stack(mul_tmp, idx_type)

    def assign(self, token):
        expr, expr_type = self._pop_stack()
        a, a_type = self._pop_stack()
        if a_type != expr_type and SymbolType.UNKNOWN not in (a_type, expr_type):
            self._handle_semantic_error(
                SemanticErrorType.TYPE_MISMATCH,
                details={"got": a_type, "expected": expr_type}
            )
        self._add_code(self._create_assign_code(expr, a))
        self._push_stack(
            a,
            symbol_type=a_type
        )

    def comparison_op(self, token):
        self.last_operator = token[1]

    def comparison(self, token):
        b, _ = self._pop_stack()
        a, _ = self._pop_stack()
        tmp = self._get_temp()
        if self.last_operator == "==":
            self._add_code(self._create_eq_code(a, b, tmp))
        elif self.last_operator == "<":
            self._add_code(self._create_lt_code(a, b, tmp))
        self._push_stack(tmp, SymbolType.VARIABLE)

    def save_if(self, token):
        expr, _ = self._pop_stack()
        self.if_stack.append(IfDetails(len(self.pb)))
        self._add_code(self._create_jpf_code(expr, Address("", AddressType.UNKNOWN)))

    def if_else_jpf(self, token):
        if_details: IfDetails = self.if_stack[-1]
        if_details.else_jp_pb_idx = len(self.pb)
        self._add_code(self._create_jp_code(Address("", AddressType.UNKNOWN)))
        self.pb[if_details.condition_jpf_pb_idx].b = self._jump_address_str(Address(
            str(len(self.pb)), AddressType.CONST
        ))

    def end_if(self, _):
        self.if_stack.pop()

    def if_jpf(self, token):
        self.pb[self.if_stack[-1].condition_jpf_pb_idx].b = self._jump_address_str(Address(
            str(len(self.pb)), AddressType.CONST
        ))

    def else_jp(self, token):
        self.pb[self.if_stack[-1].else_jp_pb_idx].a = self._jump_address_str(Address(
            str(len(self.pb)), AddressType.CONST
        ))

    def arith_op(self, token):
        self.arith_operator_stack.append(token[1])

    def arith(self, token):
        op = self.arith_operator_stack.pop()
        b, b_symbol_type = self._pop_stack()
        a, a_symbol_type = self._pop_stack()
        if SymbolType.UNKNOWN in (a_symbol_type, b_symbol_type):
            self._push_stack(self.__dummy_symbol().address, SymbolType.UNKNOWN)
            return
        if a_symbol_type != b_symbol_type:
            self._handle_semantic_error(SemanticErrorType.TYPE_MISMATCH, details={
                "got": a_symbol_type, "expected": b_symbol_type,
            })
            self._push_stack(self.__dummy_symbol().address, SymbolType.UNKNOWN)
            return
        tmp = self._get_temp()
        if op == "+":
            self._add_code(self._create_add_code(a, b, tmp))
        else:
            self._add_code(self._create_sub_code(a, b, tmp))
        self._push_stack(tmp, a_symbol_type)

    def mult(self, token):
        b, b_symbol_type = self._pop_stack()
        a, a_symbol_type = self._pop_stack()
        if SymbolType.UNKNOWN in (a_symbol_type, b_symbol_type):
            self._push_stack(self.__dummy_symbol().address, SymbolType.UNKNOWN)
            return
        if a_symbol_type != b_symbol_type:
            self._handle_semantic_error(SemanticErrorType.TYPE_MISMATCH, details={
                "got": a_symbol_type, "expected": b_symbol_type,
            })
            self._push_stack(self.__dummy_symbol().address, SymbolType.UNKNOWN)
            return
        tmp = self._get_temp()
        self._add_code(self._create_mult_code(a, b, tmp))
        self._push_stack(tmp, a_symbol_type)

    def negate(self, token):
        a, a_type = self._pop_stack()
        tmp = self._get_temp()
        self._add_code(self._create_sub_code(Address("0", AddressType.CONST), a, tmp))
        self._push_stack(tmp, a_type)

    def pop_stack(self, _):
        self._pop_stack()

    def start_iterator_expression_mode(self, token):
        self.iterator_expression_mode = True

    def end_iterator_expression_mode(self, token):
        self.iterator_expression_mode = False

    def start_for(self, _):
        self.loop_stack.append(
            LoopDetails(
                len(self.pb),
                self.scanner.lineno,
            )
        )

    def end_for(self, _):
        loop_details: LoopDetails = self.loop_stack.pop()
        self._running_iterator_expression = True
        self._iterator_expression_lineno = loop_details.lineno
        for action_symbol, token in loop_details.iterator_expression_pb:
            self.__call__(action_symbol, token)
        self._running_iterator_expression = False
        self.pb.append(
            self._create_jp_code(
                Address(str(loop_details.label_pb_idx), AddressType.CONST)
            )
        )
        loop_details.next_pb_idx = len(self.pb)
        next_address = Address(str(len(self.pb)), AddressType.CONST)
        for break_pb_idx in loop_details.breaks_pb_idx:
            self.pb[break_pb_idx] = self._create_jp_code(next_address)
        self.pb[loop_details.condition_jp_pb_idx].b = self._jump_address_str(
            next_address
        )

    def save_for(self, _):
        self.loop_stack[-1].condition_jp_pb_idx = len(self.pb)
        a, _ = self._pop_stack()
        self._add_code(
            self._create_jpf_code(a, Address("", address_type=AddressType.UNKNOWN))
        )

    def set_return_value(self, _):
        a, _ = self._pop_stack()
        self._add_code(self._create_assign_code(a, self.func_stack[-1].return_value_address))

    def start_function_call(self, _):
        func = self.func_map.get(self.last_variable, None)
        self._pop_stack()
        if func is None:
            return
        self.func_call_stack.append(FunctionCallDetails(function=func))

    def add_arg(self, _):
        address, symbol_type = self._pop_stack()
        self.func_call_stack[-1].args.append(
            ArgDetails(name="", address=address, arg_type=symbol_type)
        )

    def end_function_call(self, _):
        call_details: FunctionCallDetails = self.func_call_stack.pop()
        if len(call_details.args) != len(call_details.function.args):
            self._handle_semantic_error(SemanticErrorType.FUNCTION_PARAM_NUMBER, {"ID": call_details.function.name})
            self._push_stack(
                self.__dummy_symbol().address,
                SymbolType.UNKNOWN
            )
            return
        for i, (arg_detail, call_arg_detail) in enumerate(zip(
                call_details.function.args, call_details.args
        )):
            if arg_detail.arg_type != call_arg_detail.arg_type and call_arg_detail.arg_type != SymbolType.UNKNOWN:
                self._handle_semantic_error(
                    SemanticErrorType.FUNCTION_PARAM_TYPE_MISMATCH,
                    details={
                        "got": call_arg_detail.arg_type,
                        "expected": arg_detail.arg_type,
                        "func_name": call_details.function.name,
                        "arg_num": i + 1,
                    }
                )
                self._push_stack(
                    self.__dummy_symbol().address,
                    SymbolType.UNKNOWN
                )
                return
        if call_details.function.name == "output":
            self._add_code(
                self._create_output_code(call_details.args[0].address)
            )
            self._push_stack(
                Address("", AddressType.UNKNOWN),
                SymbolType.VARIABLE,
            )
            return
        ra = None
        if self.func.name != "main":
            ra = self.func.return_address
            self._save_in_stack(ra)
        for symbol in self._get_this_scope_symbol():
            if symbol.address.address_type != AddressType.CONST:
                self._save_in_stack(symbol.address)
        for address in self.stack:
            if address.address_type != AddressType.CONST:
                self._save_in_stack(address)
        for arg_detail, call_arg_detail in zip(
                call_details.function.args, call_details.args
        ):
            self._add_code(
                self._create_assign_code(
                    call_arg_detail.address,
                    arg_detail.address
                )
            )

        self._add_code(
            self._create_assign_code(
                Address(str(len(self.pb) + 2), AddressType.CONST),
                call_details.function.return_address,
            )
        )

        self._add_code(
            self._create_jp_code(
                Address(
                    str(call_details.function.pb_idx), address_type=AddressType.CONST
                )
            )
        )

        for address in reversed(self.stack):
            if address.address_type != AddressType.CONST:
                self._restore_from_stack(address)

        for symbol in reversed(self._get_this_scope_symbol()):
            if symbol.address.address_type != AddressType.CONST:
                self._restore_from_stack(symbol.address)
        if self.func.name != "main":
            self._restore_from_stack(ra)

        if call_details.function.data_type != SymbolDataType.VOID:
            tmp = self._get_temp()
            self._add_code(
                self._create_assign_code(
                    call_details.function.return_value_address,
                    tmp
                )
            )
            self._push_stack(
                tmp,
                SymbolType.VARIABLE,
            )
        else:
            self._push_stack(
                Address("", AddressType.UNKNOWN),
                SymbolType.VARIABLE,
            )

    def _restore_from_stack(self, address):
        self._add_code(
            self._create_sub_code(
                self.STACK_POINTER_ADDRESS,
                Address(str(self.INT_SIZE), address_type=AddressType.CONST),
                self.STACK_POINTER_ADDRESS,
            )
        )
        self._add_code(
            self._create_assign_code(
                self.STACK_ADDRESS,
                Address(address.address, address_type=AddressType.IMMEDIATE),
            )
        )

    def _save_in_stack(self, address):
        self._add_code(self._create_assign_code(
            Address(address=address.address, address_type=AddressType.IMMEDIATE), self.STACK_ADDRESS))
        self._add_code(
            self._create_add_code(
                self.STACK_POINTER_ADDRESS,
                Address(str(self.INT_SIZE), address_type=AddressType.CONST),
                self.STACK_POINTER_ADDRESS,
            )
        )

    def check_array(self, token):
        return self._get_symbol(self.last_variable).symbol_type == SymbolType.ARRAY

    def check_declaration_var(self, _):
        return self.declaration.data_type != SymbolDataType.VOID

    def check_var(self, token):
        s = self._get_symbol(self.last_variable)
        if s is not None:
            return s.symbol_type != SymbolType.FUNCTION

    def check_function(self, token):
        s = self._get_symbol(self.last_variable)
        if s is not None:
            return s.symbol_type == SymbolType.FUNCTION

    def _get_symbol(self, symbol) -> SymbolTableItem:
        return self.symbol_table.get_last_by_lexeme(symbol)

    def _find_address(self, symbol):
        return self.symbol_table.get_last_by_lexeme(symbol).address

    def _get_this_scope_symbol(self):
        return self.symbol_table.get_scope_symbols(self.func.scope)

    def check_return_void(self, token):
        return self.func_stack[-1].data_type == SymbolDataType.VOID

    def check_return_non_void(self, token):
        return self.func_stack[-1].data_type != SymbolDataType.VOID

    def check_redeclaration(self, token):
        last = self.symbol_table.get_last_by_lexeme(token[1])
        if last == None or last.scope != self.scope:
            return
        "handle this"

    def _get_temp(self):
        self.temp += self.INT_SIZE
        return Address(
            str(self.temp - self.INT_SIZE), address_type=AddressType.IMMEDIATE
        )

    def _reserve_for_array(self, size):
        self.temp += (size - 1) * self.INT_SIZE

    def _add_code(self, code: Code):
        self.pb.append(code)

    def _create_add_code(self, a: Address, b: Address, res: Address):
        return Code(
            "ADD",
            self._non_jump_address_str(a),
            self._non_jump_address_str(b),
            self._non_jump_address_str(res),
        )

    def _create_sub_code(self, a: Address, b: Address, res: Address):
        return Code(
            "SUB",
            self._non_jump_address_str(a),
            self._non_jump_address_str(b),
            self._non_jump_address_str(res),
        )

    def _create_assign_code(self, a: Address, r: Address):
        return Code(
            "ASSIGN",
            self._non_jump_address_str(a),
            self._non_jump_address_str(r),
        )

    def _create_jp_code(self, a: Address):
        return Code("JP", self._jump_address_str(a))

    def _create_jpf_code(self, a: Address, l: Address):
        return Code("JPF", self._non_jump_address_str(a), self._jump_address_str(l))

    def _create_mult_code(self, a: Address, b: Address, res: Address):
        return Code(
            "MULT",
            self._non_jump_address_str(a),
            self._non_jump_address_str(b),
            self._non_jump_address_str(res),
        )

    def _create_eq_code(self, a: Address, b: Address, res: Address):
        return Code(
            "EQ",
            self._non_jump_address_str(a),
            self._non_jump_address_str(b),
            self._non_jump_address_str(res),
        )

    def _create_lt_code(self, a: Address, b: Address, res: Address):
        return Code(
            "LT",
            self._non_jump_address_str(a),
            self._non_jump_address_str(b),
            self._non_jump_address_str(res),
        )

    def _create_output_code(self, a: Address):
        return Code("PRINT", self._non_jump_address_str(a))

    def _push_stack(self, element, symbol_type: SymbolType):
        self.semantic_stack.append(symbol_type)
        self.stack.append(element)

    def _pop_stack(self) -> Tuple[Address, SymbolType]:
        return self.stack.pop(), self.semantic_stack.pop()

    @staticmethod
    def _non_jump_address_str(address: Address):
        if address.address_type == AddressType.CONST:
            return f"#{address.address}"
        if address.address_type == AddressType.INDIRECT:
            return f"@{address.address}"
        if address.address_type == AddressType.IMMEDIATE:
            return address.address
        return ""

    @staticmethod
    def _jump_address_str(address: Address):
        if address.address_type == AddressType.CONST:
            return address.address
        if address.address_type == AddressType.IMMEDIATE:
            return f"@{address.address}"
        return ""

    def _handle_semantic_error(self, error_type: SemanticErrorType, details):
        self._has_error = True
        if error_type == SemanticErrorType.SCOPING:
            self.__write_semantic_error(f"'{details['ID']}' is not defined")
        elif error_type == SemanticErrorType.FUNCTION_PARAM_NUMBER:
            self.__write_semantic_error(f"Mismatch in numbers of arguments of '{details['ID']}'")
        elif error_type == SemanticErrorType.VOID_TYPE:
            self.__write_semantic_error(f"Illegal type of void for '{details['ID']}'")
        elif error_type == SemanticErrorType.TYPE_MISMATCH:
            self.__write_semantic_error(f"Type mismatch in operands, Got "
                                        f"{self.__transform_symbol_type_for_semantic(details['got'])} instead of"
                                        f" {self.__transform_symbol_type_for_semantic(details['expected'])}")
        elif error_type == SemanticErrorType.BREAK:
            self.__write_semantic_error(f"No 'for' found for 'break'")
        elif error_type == SemanticErrorType.FUNCTION_PARAM_TYPE_MISMATCH:
            self.__write_semantic_error(f"Mismatch in type of argument {details['arg_num']} of '{details['func_name']}'"
                                        f". Expected '{self.__transform_symbol_type_for_semantic(details['expected'])}'"
                                        f" but got '{self.__transform_symbol_type_for_semantic(details['got'])}' instead")

    @staticmethod
    def __transform_symbol_type_for_semantic(symbol_type: SymbolType) -> str:
        if symbol_type == SymbolType.ARRAY:
            return "array"
        if symbol_type == SymbolType.VARIABLE:
            return "int"
        if symbol_type == SymbolType.FUNCTION:
            return "function"

    def __write_semantic_error(self, error: str):
        if not self._running_iterator_expression:
            lineno = self.scanner.lineno
        else:
            lineno = self._iterator_expression_lineno
        self._semantic_errors.append(SemanticError(lineno, error))

    @staticmethod
    def __dummy_symbol():
        return SymbolTableItem(
            0,
            "",
            SymbolType.UNKNOWN,
            address=Address(address="", address_type=AddressType.UNKNOWN),
            data_type=SymbolDataType.UNKNOWN
        )
