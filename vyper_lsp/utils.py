import logging
import string
import re
from pathlib import Path
from importlib.metadata import version
from typing import Optional, Tuple
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from packaging.version import Version
from pygls.workspace import Document
from vyper.ast import VyperNode
from vyper.exceptions import VyperException
from vyper.compiler import FileInput

logger = logging.getLogger("vyper-lsp")


def get_installed_vyper_version():
    return Version(version("vyper"))


def get_source(filepath):
    base_path = Path(__file__).parent.parent
    filepath = base_path / filepath
    return filepath.read_text()


# detect if current line is a variable declaration
def is_var_declaration(line):
    # regex for variable declaration
    # should match lines starting with any identifier followed by a colon
    # like "foo: "
    reg = r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:"
    return bool(re.match(reg, line.strip()))


def is_attribute_access(line):
    # regex for attribute access
    # should match lines ending with a dot
    # like "foo."
    reg = r"\s*\.\s*$"
    return bool(re.match(reg, line.strip()))


_WORD_CHARS = string.ascii_letters + string.digits + "_"


# REVIEW: these get_.*_at_cursor helpers would benefit from having
# access to as much cursor information as possible (ex. line number),
# it could open up some possibilies when refactoring for performance


def get_word_at_cursor(sentence: str, cursor_index: int) -> str:
    start = cursor_index
    end = cursor_index

    # TODO: this could be a perf hotspot
    # Find the start of the word
    while start > 0 and sentence[start - 1] in _WORD_CHARS:
        start -= 1

    # Find the end of the word
    while end < len(sentence) and sentence[end] in _WORD_CHARS:
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word


def _check_if_cursor_is_within_parenthesis(sentence: str, cursor_index: int) -> bool:
    # Find the nearest '(' before the cursor
    start = sentence[:cursor_index][::-1].find("(")
    if start != -1:
        start = cursor_index - start - 1

    # Find the nearest ')' after the cursor
    end = sentence[cursor_index:].find(")")
    if end != -1:
        end += cursor_index

    # Check if cursor is within a valid pair of parentheses
    if start != -1 and end != -1 and start < cursor_index < end:
        return True

    return False


def _get_entire_function_call(sentence: str, cursor_index: int) -> str:
    # Regex pattern to match function calls
    # This pattern looks for a word (function name), followed by optional spaces,
    # and then parentheses with anything inside.
    pattern = r"\b(?:\w+\.)*\w+\s*\([^)]*\)"

    # Find all matches in the sentence
    matches = [match for match in re.finditer(pattern, sentence)]

    # Find the match that contains the cursor
    for match in matches:
        if match.start() <= cursor_index <= match.end():
            return match.group()

    return ""  # Return an empty string if no match is found


def get_expression_at_cursor(sentence: str, cursor_index: int) -> str:
    if _check_if_cursor_is_within_parenthesis(sentence, cursor_index):
        return _get_entire_function_call(sentence, cursor_index)

    # does the same thing as get_word_at_cursor but includes . and [ and ] in the expression
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    while start > 0 and sentence[start - 1] in _WORD_CHARS + ".[]":
        start -= 1

    # Find the end of the word
    while end < len(sentence) and sentence[end] in _WORD_CHARS + ".[]":
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word


def extract_enum_name(line: str):
    m = re.match(r"enum\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:", line)
    if m:
        return m.group(1)
    return None


def range_from_node(node: VyperNode) -> Range:
    return Range(
        start=Position(line=node.lineno - 1, character=node.col_offset),
        end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
    )


def range_from_exception(node: VyperException) -> Range:
    if getattr(node, "end_lineno", None) is None:
        return Range(
            start=Position(line=node.lineno - 1, character=node.col_offset),
            end=Position(line=node.lineno - 1, character=node.col_offset),
        )
    return Range(
        start=Position(line=node.lineno - 1, character=node.col_offset),
        end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
    )


def create_diagnostic_warning(
    line_num: int, character_start: int, character_end: int, message: str
) -> Diagnostic:
    """
    Helper function to create a diagnostic object.

    :param line_num: The line number of the diagnostic.
    :param character_start: The starting character position of the diagnostic.
    :param character_end: The ending character position of the diagnostic.
    :param message: The diagnostic message.
    :return: A Diagnostic object.
    """
    return Diagnostic(
        range=Range(
            start=Position(line=line_num, character=character_start),
            end=Position(line=line_num, character=character_end),
        ),
        message=message,
        severity=DiagnosticSeverity.Warning,
    )


def diagnostic_from_exception(node: VyperException, message=None) -> Diagnostic:
    return Diagnostic(
        range=range_from_exception(node),
        message=message or str(node),
        severity=DiagnosticSeverity.Error,
    )


def document_to_fileinput(doc: Document) -> FileInput:
    path = Path(doc.uri.replace("file://", ""))
    return FileInput(0, path, path, doc.source)


def working_directory_for_document(doc: Document) -> Path:
    return Path(doc.uri.replace("file://", "")).parent


def escape_underscores(expression: str) -> str:
    return expression.replace("_", "\\_")


def format_fn(func) -> str:
    args = ", ".join([f"{arg.name}: _{arg.typ}_" for arg in func.arguments])
    return_value = f" -> _{func.return_type}_" if func.return_type is not None else ""
    mutability = func.mutability.value
    out = (
        f"def __{escape_underscores(func.name)}__({args}){return_value}: _{mutability}_"
    )
    return out


def parse_fncall_expression(expression: str) -> Optional[Tuple[str, str]]:
    # regex for matching 'module.function' or 'module.function(args)', not capturing args
    fncall_pattern = "(.*)\\.([^\\(]+)(?:\\(.*\\))?"

    if matches := re.match(fncall_pattern, expression):
        groups = matches.groups()
        module, fn = groups
        if "(" in module:
            module = module.split("(")[-1]
        return module, fn
