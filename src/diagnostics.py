import sys
import warnings
from lark import UnexpectedInput, UnexpectedToken
from pygls.lsp.types.language_features import Diagnostic, List, Position, Range
from pygls.workspace import Document
from vyper.compiler import CompilerData
from vyper.exceptions import VyperException

from .parse import parser
import re

pattern = r"(.+) is deprecated\. Please use `(.+)` instead\."
compiled_pattern = re.compile(pattern)

def format_parse_error(e):
    if isinstance(e, UnexpectedToken):
        expected = ", ".join(e.accepts or e.expected)
        return f"Unexpected token '{e.token}' at {e.line}:{e.column}. Expected one of: {expected}"
    else:
        return str(e)


def get_diagnostics(doc: Document):
    doctext = doc.source
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

    warnings.simplefilter("always")
    replacements = {}
    with warnings.catch_warnings(record=True) as w:
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
                        severity=1,
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
                            severity=1,
                        )
                    )
        print(f"{len(w)} warnings", file=sys.stderr)
        for warning in w:
            match = compiled_pattern.match(str(warning.message))
            if not match:
                continue
            deprecated = match.group(1)
            replacement = match.group(2)
            replacements[deprecated] = replacement

    # iterate over doc.lines and find all deprecated values
    # and create a warning for each one at the correct position
    for i, line in enumerate(doc.lines):
        for deprecated, replacement in replacements.items():
            if deprecated in line:
                diagnostics.append(
                    Diagnostic(
                        range=Range(
                            start=Position(line=i, character=line.index(deprecated)),
                            end=Position(line=i, character=line.index(deprecated) + len(deprecated)),
                        ),
                        message=f"{deprecated} is deprecated. Please use {replacement} instead.",
                        severity=2,
                    )
                )

    return diagnostics
