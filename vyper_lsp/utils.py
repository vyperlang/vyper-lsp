import re
from pathlib import Path
from importlib.metadata import version
from packaging.version import Version

from vyper.compiler import CompilerData


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
    return char.isalnum() or char == "_"


def get_word_at_cursor(sentence: str, cursor_index: int) -> str:
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    while start > 0 and is_word_char(sentence[start - 1]):
        start -= 1

    # Find the end of the word
    while end < len(sentence) and is_word_char(sentence[end]):
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word


def get_expression_at_cursor(sentence: str, cursor_index: int) -> str:
    # does the same thing as get_word_at_cursor but includes . and [ and ] in the expression
    start = cursor_index
    end = cursor_index

    # Find the start of the word
    while start > 0 and sentence[start - 1].isalnum() or sentence[start - 1] in ".[]()":
        start -= 1

    # Find the end of the word
    while end < len(sentence) and sentence[end].isalnum() or sentence[end] in ".[]()":
        end += 1

    # Extract the word
    word = sentence[start:end]

    return word


def extract_enum_name(line: str):
    match = re.match(r"enum\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*:", line)
    if match:
        return match.group(1)
    return None
