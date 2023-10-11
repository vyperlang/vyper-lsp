from lark import UnexpectedInput, UnexpectedToken
from pygls.lsp.types.language_features import Diagnostic, List, Position, Range
from vyper.compiler import CompilerData
from vyper.exceptions import VyperException

from .parse import parser


def format_parse_error(e):
    if isinstance(e, UnexpectedToken):
        expected = ", ".join(e.accepts or e.expected)
        return f"Unexpected token '{e.token}' at {e.line}:{e.column}. Expected one of: {expected}"
    else:
        return str(e)


def get_diagnostics(doctext: str):
    diagnostics: List[Diagnostic] = []
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
        parser.parse(doctext, on_error=on_error)
    except Exception:
        # ignore errors that are already handled by on_error
        pass

    compiler_data = CompilerData(doctext)

    try:
        compiler_data.vyper_module_unfolded
    except VyperException as e:
        if e.lineno is not None and e.col_offset is not None:
            diagnostics.append(
                Diagnostic(
                    range=Range(
                        start=Position(line=e.lineno - 1, character=e.col_offset - 1),
                        end=Position(line=e.lineno - 1, character=e.col_offset),
                    ),
                    message=str(e),
                )
            )
        else:
            for a in e.annotations:
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(
                                line=a.lineno - 1, character=a.col_offset - 1
                            ),
                            end=Position(line=a.lineno - 1, character=a.col_offset),
                        ),
                        message=e.message,
                    )
                )

    return diagnostics
