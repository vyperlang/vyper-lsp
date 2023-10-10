from pygls.server import LanguageServer
import sys
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
)
import re
from pygls.lsp.types.language_features import CompletionOptions, CompletionList, CompletionItem, CompletionParams
from .types import BASE_TYPES
from vyper.ast.grammar import parse_vyper_source

DECORATORS = ["public", "private", "constant", "payable", "nonpayable", "view", "pure", "external"]

server = LanguageServer('vyper', 'v0.0.1')

# detect if current line is a variable declaration
def is_var_declaration(line):

    # regex for variable declaration
    # should match lines starting with any identifier followed by a colon
    # like "foo: "
    reg = r"^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*:"
    # print to stderr
    return bool(re.match(reg, line.strip()))

def is_attribute_access(line):
    # regex for attribute access
    # should match lines ending with a dot
    # like "foo."
    reg = r"\s*\.\s*$"
    return bool(re.match(reg, line.strip()))

@server.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[":", ".", "@"]))
def completions(ls, params: CompletionParams):
    items = []
    document = server.workspace.get_document(params.text_document.uri)
    og_line = document.lines[params.position.line]
    current_line = document.lines[params.position.line].strip()

    if params.context:
        if params.context.trigger_character == ".":
            print(f"trigger character is {params.context.trigger_character}", file=sys.stderr)
        elif params.context.trigger_character == "@":
            print(f"trigger character is {params.context.trigger_character}", file=sys.stderr)
            for dec in DECORATORS:
                items.append(CompletionItem(label=dec))
            l = CompletionList(is_incomplete=False, items=[])
            l.add_items(items)
            return l
        elif params.context.trigger_character == ":":
            for typ in BASE_TYPES:
                if og_line.endswith(" "):
                    items.append(CompletionItem(label=typ))
                else:
                    items.append(CompletionItem(label=typ, insert_text=f" {typ}"))

            l = CompletionList(is_incomplete=False, items=[])
            l.add_items(items)
            return l
    return CompletionList(is_incomplete=False, items=[])

def main():
    server.start_io()
