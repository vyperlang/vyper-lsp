import argparse
from typing import Optional, List
import logging
from .logging import LanguageServerLogHandler
from lsprotocol.types import (
    TEXT_DOCUMENT_COMPLETION,
    TEXT_DOCUMENT_DID_CHANGE,
    TEXT_DOCUMENT_DID_OPEN,
    TEXT_DOCUMENT_DID_SAVE,
    TEXT_DOCUMENT_DECLARATION,
    TEXT_DOCUMENT_DEFINITION,
    TEXT_DOCUMENT_IMPLEMENTATION,
    TEXT_DOCUMENT_REFERENCES,
    TEXT_DOCUMENT_HOVER,
    TEXT_DOCUMENT_SIGNATURE_HELP,
    CompletionOptions,
    CompletionParams,
    CompletionList,
    DeclarationParams,
    ReferenceParams,
    DefinitionParams,
    HoverParams,
    Hover,
    SignatureHelpOptions,
    SignatureHelpParams,
    Location,
    DidChangeTextDocumentParams,
    DidOpenTextDocumentParams,
    DidSaveTextDocumentParams,
)
from packaging.version import Version
from pygls.server import LanguageServer
from vyper_lsp.handlers.signatures import SignatureHandler
from vyper_lsp.handlers.completion import CompletionHandler
from vyper_lsp.handlers.hover import HoverHandler
from vyper_lsp.debounce import Debouncer

from vyper_lsp.navigation import ASTNavigator
from vyper_lsp.utils import get_installed_vyper_version


from .ast import AST

ast = AST()

server = LanguageServer("vyper", "v0.0.1")
navigator = ASTNavigator(ast)

completer = CompletionHandler(ast)
signature_handler = SignatureHandler(ast)
hover_handler = HoverHandler(ast)

debouncer = Debouncer(wait=0.5)

logger = logging.getLogger("vyper-lsp")


def _check_minimum_vyper_version():
    vy_version = get_installed_vyper_version()
    min_version = Version("0.4.0")
    if vy_version < min_version:
        raise Exception(
            f"vyper version {vy_version} is not supported, please upgrade to {min_version} or higher"
        )


@debouncer.debounce
def validate_doc(
    ls: LanguageServer,
    params: DidOpenTextDocumentParams
    | DidChangeTextDocumentParams
    | DidSaveTextDocumentParams,
):
    logger.info("validating doc")
    text_doc = ls.workspace.get_text_document(params.text_document.uri)
    ast_diagnostics = ast.update_ast(text_doc)
    ls.publish_diagnostics(params.text_document.uri, ast_diagnostics)


@server.feature(TEXT_DOCUMENT_DID_OPEN)
async def did_open(ls: LanguageServer, params: DidOpenTextDocumentParams):
    _check_minimum_vyper_version()
    handler = LanguageServerLogHandler(ls)
    logger.addHandler(handler)
    validate_doc(ls, params)


@server.feature(TEXT_DOCUMENT_DID_CHANGE)
async def did_change(ls: LanguageServer, params: DidChangeTextDocumentParams):
    validate_doc(ls, params)


@server.feature(TEXT_DOCUMENT_DID_SAVE)
async def did_save(ls: LanguageServer, params: DidSaveTextDocumentParams):
    validate_doc(ls, params)


@server.feature(
    TEXT_DOCUMENT_COMPLETION, CompletionOptions(trigger_characters=[":", ".", "@"])
)
def completions(ls, params: CompletionParams) -> CompletionList:
    return completer.get_completions(ls, params)


@server.feature(TEXT_DOCUMENT_DECLARATION)
def go_to_declaration(
    ls: LanguageServer, params: DeclarationParams
) -> Optional[Location]:
    document = ls.workspace.get_text_document(params.text_document.uri)
    range = navigator.find_declaration(document, params.position)
    if range:
        return Location(uri=params.text_document.uri, range=range)
    else:
        ls.show_message("No declaration found")


@server.feature(TEXT_DOCUMENT_DEFINITION)
def go_to_definition(
    ls: LanguageServer, params: DefinitionParams
) -> Optional[Location]:
    # TODO: Look for assignment nodes to find definition
    document = ls.workspace.get_text_document(params.text_document.uri)
    range_ = navigator.find_declaration(document, params.position)
    if range_:
        return Location(uri=params.text_document.uri, range=range_)


@server.feature(TEXT_DOCUMENT_REFERENCES)
def find_references(ls: LanguageServer, params: ReferenceParams) -> List[Location]:
    document = ls.workspace.get_text_document(params.text_document.uri)
    return [
        Location(uri=params.text_document.uri, range=range_)
        for range_ in navigator.find_references(document, params.position)
    ]


@server.feature(TEXT_DOCUMENT_HOVER)
def hover(ls: LanguageServer, params: HoverParams):
    document = ls.workspace.get_text_document(params.text_document.uri)
    hover_info = hover_handler.hover_info(document, params.position)
    if hover_info:
        return Hover(contents=hover_info, range=None)


@server.feature(
    TEXT_DOCUMENT_SIGNATURE_HELP,
    SignatureHelpOptions(trigger_characters=["("], retrigger_characters=[",", " "]),
)
def signature_help(ls: LanguageServer, params: SignatureHelpParams):
    document = ls.workspace.get_text_document(params.text_document.uri)
    signature_info = signature_handler.signature_help(document, params)
    if signature_info:
        return signature_info


@server.feature(TEXT_DOCUMENT_IMPLEMENTATION)
def implementation(ls: LanguageServer, params: DefinitionParams):
    document = ls.workspace.get_text_document(params.text_document.uri)
    range_ = navigator.find_implementation(document, params.position)
    if range_:
        return Location(uri=params.text_document.uri, range=range)


def main():
    parser = argparse.ArgumentParser(
        description="Start the server with specified protocol and options."
    )
    parser.add_argument("--stdio", action="store_true", help="Use stdio protocol")
    parser.add_argument(
        "--tcp",
        nargs=2,
        metavar=("HOST", "PORT"),
        help="Use TCP protocol with specified host and port",
    )

    args = parser.parse_args()

    if args.tcp:
        host, port = args.tcp
        server.start_tcp(host=host, port=int(port))
    else:
        # Default to stdio if --tcp is not provided
        server.start_io()
