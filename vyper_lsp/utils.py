import logging
import re
from pathlib import Path
from importlib.metadata import version
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from packaging.version import Version
from vyper.ast import VyperNode
from vyper.exceptions import VyperException

from vyper.compiler import CompilerData

logger = logging.getLogger("vyper-lsp")


def get_installed_vyper_version():
    return Version(version("vyper"))


def get_source(filepath):
    base_path = Path(__file__).parent.parent
    filepath = base_path / filepath
    return filepath.read_text()


def get_compiler_data(filepath):
    source = get_source(filepath)
    return CompilerData(source)


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


def is_word_char(char):
    # true for alnum and underscore
    # REVIEW: another possibility is `char in <possible char string>`
    # ex. `char in "_" + string.ascii_letters + string.digits`.
    # the constants can be factored out for small performance
    return char.isalnum() or char == "_"


# REVIEW: these get_.*_at_cursor helpers would benefit from having
# access to as much cursor information as possible (ex. line number),
# it could open up some possibilies when refactoring for performance


def get_word_at_cursor(sentence: str, cursor_index: int) -> str:
    start = cursor_index
    end = cursor_index

    # TODO: this could be a perf hotspot
    # Find the start of the word
    while start > 0 and is_word_char(sentence[start - 1]):
        start -= 1

    # Find the end of the word
    while end < len(sentence) and is_word_char(sentence[end]):
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word


def _check_if_cursor_is_within_parenthesis(sentence: str, cursor_index: int) -> bool:
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    # TODO: this is a hacky way to do this, should be refactored
    # REVIEW: could be reversed(sentence[:start]).find("(")
    while start > 0 and sentence[start] != "(":
        start -= 1

    # Find the end of the word
    # TODO: this is a hacky way to do this, should be refactored
    # REVIEW: could be sentence[cursor_index:].find(")")
    while end < len(sentence) and sentence[end] != ")":
        end += 1

    if start != 0 and start < cursor_index and cursor_index < end:
        return True

    return False


def _get_entire_function_call(sentence: str, cursor_index: int) -> str:
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    # only skip spaces if we're within the parenthesis
    # REVIEW: what about `foo (x)`?
    while start > 0 and sentence[start - 1] != "(":
        start -= 1

    while start > 0 and sentence[start - 1] != " ":
        start -= 1

    # Find the end of the word
    while end < len(sentence) and sentence[end] != ")":
        end += 1

    fn_call = sentence[start:end]
    return fn_call


def get_expression_at_cursor(sentence: str, cursor_index: int) -> str:
    if _check_if_cursor_is_within_parenthesis(sentence, cursor_index):
        return _get_entire_function_call(sentence, cursor_index)

    # does the same thing as get_word_at_cursor but includes . and [ and ] in the expression
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    # REVIEW: maybe sentence[start - 1] in `_WORD_CHARS + ".[]()"`
    while start > 0 and (
        is_word_char(sentence[start - 1]) or sentence[start - 1] in ".[]()"
    ):
        start -= 1

    # Find the end of the word
    while end < len(sentence) and (
        is_word_char(sentence[end]) or sentence[end] in ".[]()"
    ):
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word


def get_internal_fn_name_at_cursor(sentence: str, cursor_index: int) -> str:
    # TODO: dont assume the fn call is at the end of the line
    # REVIEW: make cases like self.foo(self.bar()) work
    word = sentence.split("(")[0].split(" ")[-1].strip().split("self.")[-1]

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
    return Range(
        start=Position(line=node.lineno - 1, character=node.col_offset),
        end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
    )


def diagnostic_from_exception(node: VyperException) -> Diagnostic:
    return Diagnostic(
        range=range_from_exception(node),
        message=str(node),
        severity=DiagnosticSeverity.Error,
    )


# this looks like duplicated code, could be in utils
def is_internal_fn(expression: str) -> bool:
    return expression.startswith("self.") and "(" in expression


# this looks like duplicated code, could be in utils
def is_state_var(expression: str) -> bool:
    return expression.startswith("self.") and "(" not in expression
