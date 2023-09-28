from pygls.server import LanguageServer
import sys
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    CompletionParams,
)

from pygls.lsp.types.language_features import CompletionOptions, CompletionList, CompletionItem

server = LanguageServer('vyper', 'v0.0.1')


@server.feature(TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[":"]))
def completions(ls, params: CompletionParams):
    items = []
    document = server.workspace.get_document(params.text_document.uri)
    og_line = document.lines[params.position.line]
    current_line = document.lines[params.position.line].strip()
    print(current_line, file=sys.stderr)
    if current_line.endswith(":"):
        if og_line[-1] != " ":
            items = [
                CompletionItem(label="uint256", insert_text=" uint256"),
                CompletionItem(label="address", insert_text=" address"),
                CompletionItem(label="bool", insert_text=" bool"),
            ]
        else:
            items = [
                    CompletionItem(label="uint256"),
                    CompletionItem(label="address"),
                    CompletionItem(label="bool"),
                ]
    print(items, file=sys.stderr)
    l = CompletionList(is_incomplete=False, items=[])
    l.add_items(items)
    return l

def main():
    server.start_io()
