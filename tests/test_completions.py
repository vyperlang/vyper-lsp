from pygls.lsp.types import CompletionContext, CompletionParams, Position
from pygls.workspace import Document

from vyper_lsp.analyzer.AstAnalyzer import AstAnalyzer


def test_completion(ast):
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
        text_document={"uri": doc.uri, "source": src}, position=pos, context=context
    )

    analyzer = AstAnalyzer(ast)
    completions = analyzer.get_completions_in_doc(doc, params)
    assert len(completions.items) == 1
    assert "foo" in [c.label for c in completions.items]
