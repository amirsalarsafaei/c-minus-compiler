import string
from enum import Enum

KEYWORDS = ("if", "else", "void", "int", "for", "break", "return", "endif")
SYMBOLS = (";", ":", ",", "[", "]", "(", ")", "{", "}", "+", "-", "<")
WHITE_SPACES = (" ", "\n", "\r", "\t", "\v", "\f")
END_OF_FILE = ("$",)
VALID_INPUTS = (
    END_OF_FILE
    + SYMBOLS
    + WHITE_SPACES
    + ("=", "*", "/")
    + tuple(string.ascii_letters)
    + tuple(string.digits)
)


class TokenType(Enum):
    KEYWORD = 1
    ID = 2
    NUM = 3
    SYMBOL = 4
    ID_OR_KEYWORD = 5
    WHITESPACE = 6
    COMMENT = 7
    END_OF_FILE = 8


class ScannerErrorType(Enum):
    INVALID_INPUT = 1
    UNCLOSED_COMMENT = 2
    UNMATCHED_COMMENT = 3
    INVALID_NUMBER = 4


class ParserErrorType(Enum):
    TOKEN_MISMATCH = 0
    ILLEGAL_TOKEN = 1
    MISSING_NON_TERMINAL = 2
    UNEXPECTED_EOF = 3


class SemanticErrorType(Enum):
    SCOPING = 0
    VOID_TYPE = 1
    FUNCTION_PARAM_NUMBER = 2
    BREAK = 4
    TYPE_MISMATCH = 5
    FUNCTION_PARAM_TYPE_MISMATCH = 6


class SymbolType(Enum):
    FUNCTION = 0
    VARIABLE = 1
    ARRAY = 2
    UNKNOWN = 3


class SymbolDataType(Enum):
    INT = 0
    VOID = 1
    UNKNOWN = 2


class AddressType(Enum):
    IMMEDIATE = 0
    INDIRECT = 1
    CONST = 2
    UNKNOWN = 3
