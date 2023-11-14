from lsprotocol.types import Position, SignatureHelpParams, TextDocumentIdentifier
from pygls.workspace import Document
from vyper_lsp.ast import AST
from vyper_lsp.analyzer.AstAnalyzer import AstAnalyzer


def test_signature_help(ast: AST):
    src = """
@internal
def foo(x: int128, y: int128) -> int128:
    return x + y

@external
def bar():
    self.foo(1, 2)
"""
    ast.build_ast(src)

    doc = Document(uri="examples/Foo.vy", source=src)

    pos = Position(line=7, character=13)
    params = SignatureHelpParams(
        text_document=TextDocumentIdentifier(doc.uri), position=pos
    )

    analyzer = AstAnalyzer(ast)
    sig_help = analyzer.signature_help(doc, params)
    assert sig_help
    assert sig_help.active_signature == 0
    assert sig_help.signatures[0].active_parameter == 1
    assert sig_help.signatures[0].label == "foo(x: int128, y: int128) -> int128"
