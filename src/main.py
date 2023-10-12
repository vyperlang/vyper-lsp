import sys
from typing import Optional
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DECLARATION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_REFERENCES
)
from pygls.lsp.types import (
    CompletionOptions,
    CompletionParams,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
)
from pygls.lsp.types.language_features import (
    CompletionList,
    DeclarationOptions,
    DeclarationParams,
    DefinitionParams,
    List,
    Location,
    Position,
    Range,
)
from pygls.server import LanguageServer
from pygls.workspace import Document

from src.completions import Completer
from src.navigation import Navigator
from src.utils import extract_enum_name, get_expression_at_cursor, get_word_at_cursor

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
    og_line = document.lines[params.position.line]
    word = get_word_at_cursor(og_line, params.position.character)
    full_word = get_expression_at_cursor(og_line, params.position.character)
    if full_word.startswith("self"):
        range = navigator.find_state_variable_declaration(word)
    else:
        range = navigator.find_type_declaration(word)
    if range:
        return Location(uri=params.text_document.uri, range=range)

@server.feature(TEXT_DOCUMENT_DEFINITION)
def go_to_definition(ls: LanguageServer, params: DefinitionParams) -> Optional[Location]:
    # TODO: Look for assignment nodes to find definition
    document = ls.workspace.get_document(params.text_document.uri)
    og_line = document.lines[params.position.line]
    word = get_word_at_cursor(og_line, params.position.character)
    range = navigator.find_type_declaration(word)
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
    og_line = document.lines[params.position.line]
    word = get_word_at_cursor(og_line, params.position.character)
    reference_ranges = navigator.find_references(word, document, params.position)
    references = []
    for range in reference_ranges:
        references.append(Location(uri=params.text_document.uri, range=range))
    return references


def main():
    server.start_io()
