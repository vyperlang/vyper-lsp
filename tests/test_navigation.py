from pygls.lsp.types import Position
from pygls.workspace import Document

from vyper_lsp.ast import AST
from vyper_lsp.navigation import ASTNavigator


def test_find_references():
    doc = Document(uri="examples/Foo.vy")
    pos = Position(line=2, character=7)
    ast = AST()
    ast.build_ast(doc.source)
    navigator = ASTNavigator(ast)
    print(doc.source)
    references = navigator.find_references(doc, pos)
    assert len(references) == 3
