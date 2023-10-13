import sys
from typing import List, Optional
from lark import UnexpectedInput, UnexpectedToken
from pygls.lsp.types import Diagnostic, Position, Range
from pygls.lsp.types.language_features import on_type_formatting
from pygls.workspace import Document
from vyper_lsp.analyzer.BaseAnalyzer import Analyzer

from pathlib import Path

import vyper
from lark import Lark
from vyper.ast.grammar import PythonIndenter

GRAMMAR_FILE_PATH = Path(vyper.__file__).parent / "ast" / "grammar.lark"
GRAMMAR = GRAMMAR_FILE_PATH.read_text()

parser = Lark(GRAMMAR, parser="lalr", start="module", postlex=PythonIndenter())

def format_parse_error(e):
    if isinstance(e, UnexpectedToken):
        expected = ", ".join(e.accepts or e.expected)
        return f"Unexpected token '{e.token}' at {e.line}:{e.column}. Expected one of: {expected}"
    else:
        return str(e)

class SourceAnalyzer(Analyzer):

    def hover_info(self, doc: Document, pos: Position) -> Optional[str]:
        return None

    def get_diagnostics(self, doc: Document) -> List[Diagnostic]:
        print(f"get_diagnostics: {doc.uri}", file=sys.stderr)
        diagnostics = []
        last_error = None

        def on_error(e: UnexpectedInput):
            nonlocal last_error
            if (
                last_error is not None
                and last_error.line == e.line
                and last_error.column == e.column
            ):
                return
            if (
                last_error is not None
                and type(last_error) == type(e)
                and last_error.line == e.line
            ):
                return
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=e.line - 1, character=e.column - 1),
                        end=Position(line=e.line - 1, character=e.column),
                    ),
                    message=format_parse_error(e),
                )
            )
            last_error = e
            return True

        try:
            parser.parse(doc.source, on_error=on_error)
        except Exception:
            # ignore errors that are already handled by on_error
            pass

        return diagnostics
