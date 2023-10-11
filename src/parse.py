from pathlib import Path

import vyper
from lark import Lark
from vyper.ast.grammar import PythonIndenter

GRAMMAR_FILE_PATH = Path(vyper.__file__).parent / "ast" / "grammar.lark"
GRAMMAR = GRAMMAR_FILE_PATH.read_text()

parser = Lark(GRAMMAR, parser="lalr", start="module", postlex=PythonIndenter())
