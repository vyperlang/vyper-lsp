from lsprotocol.types import Position, SignatureHelpParams, TextDocumentIdentifier
from pygls.workspace import Document
from vyper_lsp.ast import AST
from vyper_lsp.handlers.signatures import SignatureHandler
from vyper_lsp.handlers.hover import HoverHandler


def test_signature_help(ast: AST):
    src = """
@internal
def foo(x: int128, y: int128) -> int128:
    return x + y

@external
def bar():
    self.foo(1, 2)

@internal
def baz(x: int128) -> int128:
    return x

@external
def foobar():
    self.foo(self.baz(1), 2)
"""
    ast.build_ast(src)
    analyzer = SignatureHandler(ast)

    doc = Document(uri="<inline source code>", source=src)

    pos = Position(line=3, character=11)
    params = SignatureHelpParams(
        text_document=TextDocumentIdentifier(doc.uri), position=pos
    )
    sig_help = analyzer.signature_help(doc, params)
    assert sig_help is None

    pos = Position(line=7, character=13)
    params = SignatureHelpParams(
        text_document=TextDocumentIdentifier(doc.uri), position=pos
    )

    sig_help = analyzer.signature_help(doc, params)
    assert sig_help
    assert sig_help.active_signature == 0
    assert sig_help.signatures[0].active_parameter == 1
    assert sig_help.signatures[0].label == "foo(x: int128, y: int128) -> int128"

    pos = Position(line=15, character=22)
    params = SignatureHelpParams(
        text_document=TextDocumentIdentifier(doc.uri), position=pos
    )
    sig_help = analyzer.signature_help(doc, params)
    assert sig_help
    assert sig_help.active_signature == 0
    assert sig_help.signatures[0].active_parameter == 1
    assert sig_help.signatures[0].label == "baz(x: int128) -> int128"


def test_hover(ast: AST):
    src = """
@internal
def foo(
    x: int128,
    y: int128
) -> int128:
    return x + y

@external
def bar():
    self.foo(1, 2)

@internal
def noreturn(x: uint256):
    y: uint256 = x

@internal
def baz():
    self.noreturn(1)
"""
    ast.build_ast(src)

    doc = Document(uri="<inline source code>", source=src)

    pos = Position(line=10, character=11)

    handler = HoverHandler(ast)
    hover = handler.hover_info(doc, pos)
    assert hover
    assert (
        hover
        == """(Internal Function) def foo(
    x: int128,
    y: int128
) -> int128:"""
    )

    pos = Position(line=18, character=11)
    hover = handler.hover_info(doc, pos)
    assert hover
    assert hover == "(Internal Function) def noreturn(x: uint256):"
