from lsprotocol.types import (
    CompletionContext,
    CompletionParams,
    Position,
    TextDocumentIdentifier,
)
from pygls.workspace import Document

from vyper_lsp.analyzer.AstAnalyzer import AstAnalyzer


def test_completion_internal_fn(ast):
    src = """
@internal
def foo():
    return

@external
def bar():
    self.foo()
"""
    ast.build_ast(src)

    src += """
@external
def baz():
    self.
"""

    doc = Document(uri="examples/Foo.vy", source=src)
    pos = Position(line=11, character=7)
    context = CompletionContext(trigger_character=".", trigger_kind=2)
    params = CompletionParams(
        text_document=TextDocumentIdentifier(doc.uri), position=pos, context=context
    )

    analyzer = AstAnalyzer(ast)
    completions = analyzer.get_completions_in_doc(doc, params)
    assert len(completions.items) == 1
    assert "foo" in [c.label for c in completions.items]


def test_completions_enum_variant(ast):
    src = """
enum Foo:
    BAR
    BAZ

@internal
def foo():
    return

@external
def bar():
    self.foo()
"""
    ast.build_ast(src)

    src += """
@external
def baz():
    x: Foo = Foo.
"""

    doc = Document(uri="examples/Foo.vy", source=src)
    pos = Position(line=15, character=18)
    context = CompletionContext(trigger_character=".", trigger_kind=2)
    params = CompletionParams(
        text_document={"uri": doc.uri, "source": src}, position=pos, context=context
    )

    analyzer = AstAnalyzer(ast)
    completions = analyzer.get_completions_in_doc(doc, params)
    assert len(completions.items) == 2
    assert "BAR" in [c.label for c in completions.items]
    assert "BAZ" in [c.label for c in completions.items]
