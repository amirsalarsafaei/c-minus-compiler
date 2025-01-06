# C-Minus Compiler Front-End

This is a hand-crafted compiler front-end implementation for the C-Minus programming language, developed as part of the Compiler Design course. C-Minus is a simplified subset of C that is ideal for learning compiler construction principles. This implementation features robust error handling and full support for recursive functions. The compiler is implemented from scratch in Python without relying on compiler-compiler tools.

## Overview

This compiler front-end processes C-Minus source code through the following phases:

- Lexical Analysis (Scanner) - Hand-implemented
- Syntax Analysis (Parser) - Hand-implemented recursive descent parser
- Semantic Analysis - Symbol table and type checking

## Features

### Supported C-Minus Language Features

- Integer data type
- Arrays
- Functions with full recursive support
- Control structures (if-else, while)
- Basic arithmetic operations
- Variable declarations
- Function calls and returns with recursion handling
- Comprehensive error detection and recovery

### Compiler Components

1. **Lexical Analyzer (Scanner)**
   - Hand-crafted implementation in Python
   - Tokenizes source code into meaningful lexemes
   - Handles identifiers, numbers, and special symbols
   - Removes comments and whitespace

- Sophisticated error detection with line and column tracking
- Detailed error messages with context information
- Robust recovery mechanism to continue analysis after errors

2. **Parser**

- Pure recursive descent parsing implementation
- Builds Abstract Syntax Tree (AST)
- Implements C-Minus grammar rules
- Handles nested and recursive function calls
- Advanced error recovery for syntax errors
- Detailed error reporting with expected vs found tokens
- Panic mode recovery to continue parsing after errors
- No dependency on parser generators

3. **Semantic Analyzer**

- Comprehensive type checking system
- Multi-level scope analysis with proper nesting
- Efficient symbol table management
- Function call validation with parameter checking
- Recursive function call analysis and validation
- Detailed semantic error detection and reporting
- Context-aware error messages with suggestions
- Call stack tracking for recursive functions
