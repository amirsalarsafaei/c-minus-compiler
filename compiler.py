# Amirsalar Safaei Ghaderi 99100177
# Seyed Mostafa Hosseini 99170383
import json
from parser import Parser

from codegen import CodeGenerator
from scanner import Scanner

with open("grammar-output.json", "r") as f:
    grammar_def_dict = json.load(f)

f_input = open("input.txt", "r")
f_tokens = open("tokens.txt", "w")
f_lexical_errors = open("lexical_errors.txt", "w")
f_syntax_errors = open("syntax_errors.txt", "w")
f_symbols = open("symbol_table.txt", "w")
f_parse_tree = open("parse_tree.txt", "w")
f_codegen = open("output.txt", "w")
f_semantic_errors = open("semantic_errors.txt", "w")


scanner = Scanner(f_input, f_lexical_errors, f_symbols)
code_gen = CodeGenerator(f_codegen, f_semantic_errors, scanner)
parser = Parser(scanner, code_gen, grammar_def_dict, f_syntax_errors, f_parse_tree)

parser.parse()

if scanner.last_error_lineno == 0:
    f_lexical_errors.write("There is no lexical error.")

f_input.close()
f_tokens.close()
f_lexical_errors.close()
f_syntax_errors.close()
f_symbols.close()
f_parse_tree.close()
f_codegen.close()
f_semantic_errors.close()

