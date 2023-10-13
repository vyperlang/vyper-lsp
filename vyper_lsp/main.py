from typing import Optional
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DECLARATION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES,
)
from pygls.lsp.methods import HOVER, IMPLEMENTATION
from pygls.lsp.types import (
    CompletionOptions,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
)
from pygls.lsp.types.language_features import (
    CompletionList,
    DeclarationParams,
    DefinitionParams,
    HoverParams,
    List,
    Location,
    Hover
)
from pygls.server import LanguageServer
from pygls.workspace import Document

from vyper_lsp.completions import Completer
from vyper_lsp.navigation import Navigator
from vyper_lsp.utils import extract_enum_name

from .ast import AST
from .diagnostics import get_diagnostics

server = LanguageServer("vyper", "v0.0.1")
completer = Completer()
navigator = Navigator()
ast = AST()

def validate_doc(ls, params):
    text_doc = ls.workspace.get_document(params.text_document.uri)
    diagnostics = get_diagnostics(text_doc)
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
def completions(ls, params: CompletionParams) -> CompletionList:
    return completer.get_completions(ls, params)


@server.feature(TEXT_DOCUMENT_DECLARATION)
def go_to_declaration(ls: LanguageServer, params: DeclarationParams) -> Optional[Location]:
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_declaration(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)

@server.feature(TEXT_DOCUMENT_DEFINITION)
def go_to_definition(ls: LanguageServer, params: DefinitionParams) -> Optional[Location]:
    # TODO: Look for assignment nodes to find definition
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_declaration(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)


def get_enum_name(ls: LanguageServer, doc: Document, variant_line_no: int):
    for line_no in range(variant_line_no, 0):
        line = doc.lines[line_no]
        enum_name = extract_enum_name(line)
        if enum_name:
            return enum_name

@server.feature(TEXT_DOCUMENT_REFERENCES)
def find_references(ls: LanguageServer, params: DefinitionParams) -> List[Location]:
    document = ls.workspace.get_document(params.text_document.uri)
    return [
        Location(uri=params.text_document.uri, range=range)
        for range in navigator.find_references(document, params.position)
    ]

@server.feature(HOVER)
def hover(ls: LanguageServer, params: HoverParams):
    document = ls.workspace.get_document(params.text_document.uri)
    hover_info = navigator.get_hover_info(document, params.position)
    if hover_info:
        return Hover(contents=hover_info, range=None)

@server.feature(IMPLEMENTATION)
def implementation(ls: LanguageServer, params: DefinitionParams):
    document = ls.workspace.get_document(params.text_document.uri)
    range = navigator.find_implementation(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)


def main():
    server.start_io()
