import sys
from typing import Optional
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DECLARATION,
    TEXT_DOCUMENT_DEFINITION
)
from pygls.lsp.types import (
    CompletionOptions,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
)
from pygls.lsp.types.language_features import (
    DeclarationOptions,
    DeclarationParams,
    DefinitionParams,
    Location,
    Position,
    Range,
)
from pygls.server import LanguageServer

from src.completions import Completer
from src.utils import get_word_at_cursor

from .ast import AST
from .diagnostics import get_diagnostics

server = LanguageServer("vyper", "v0.0.1")
completer = Completer()
ast = AST()

def validate_doc(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    diagnostics = get_diagnostics(text_doc.source)
    ls.publish_diagnostics(params.text_document.uri, diagnostics)
    ast.update_ast(text_doc)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    validate_doc(ls, params)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    validate_doc(ls, params)


@server.feature(
    TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[":", ".", "@", " "])
)
def completions(ls, params: CompletionParams):
    return completer.get_completions(ls, params)


@server.feature(TEXT_DOCUMENT_DECLARATION)
def go_to_declaration(ls: LanguageServer, params: DeclarationParams) -> Optional[Location]:
    document = ls.workspace.get_document(params.text_document.uri)
    og_line = document.lines[params.position.line]
    word = get_word_at_cursor(og_line, params.position.character)
    node = ast.find_declaration_node(word)
    if node:
        range = Range(
            start=Position(line=node.lineno - 1, character=node.col_offset),
            end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
        )
        declaration: Location = Location(uri=params.text_document.uri, range=range)
        return declaration

@server.feature(TEXT_DOCUMENT_DEFINITION)
def go_to_definition(ls: LanguageServer, params: DefinitionParams) -> Optional[Location]:
    document = ls.workspace.get_document(params.text_document.uri)
    og_line = document.lines[params.position.line]
    word = get_word_at_cursor(og_line, params.position.character)
    node = ast.find_declaration_node(word)
    if node:
        range = Range(
            start=Position(line=node.lineno - 1, character=node.col_offset),
            end=Position(line=node.end_lineno - 1, character=node.end_col_offset),
        )
        declaration: Location = Location(uri=params.text_document.uri, range=range)
        return declaration



def main():
    server.start_io()
