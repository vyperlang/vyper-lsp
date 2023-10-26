from pygls.lsp.types import Position
from pygls.workspace import Document

from vyper_lsp.ast import AST
from vyper_lsp.navigation import ASTNavigator

import pytest


@pytest.fixture
def doc():
    doc = Document(uri="examples/Foo.vy")
    ast = AST()
    ast.build_ast(doc.source)
    return doc


@pytest.fixture
def navigator():
    return ASTNavigator()


def test_find_references_event_name(doc, navigator):
    pos = Position(line=2, character=7)
    references = navigator.find_references(doc, pos)
    assert len(references) == 3


def test_find_references_struct_name(doc, navigator):
    pos = Position(line=6, character=7)
    references = navigator.find_references(doc, pos)
    assert len(references) == 4


def test_find_references_enum_name(doc, navigator):
    pos = Position(line=9, character=7)
    references = navigator.find_references(doc, pos)
    assert len(references) == 5


def test_find_references_enum_variants(doc, navigator):
    pos = Position(line=10, character=7)
    references = navigator.find_references(doc, pos)
    assert len(references) == 1

    pos = Position(line=11, character=7)
    references = navigator.find_references(doc, pos)
    assert len(references) == 1


def test_find_references_function_name(doc, navigator):
    pos = Position(line=40, character=5)
    references = navigator.find_references(doc, pos)
    assert len(references) == 1


def test_find_references_storage_var(doc, navigator):
    pos = Position(line=13, character=0)
    references = navigator.find_references(doc, pos)
    assert len(references) == 3


def test_find_declaration_constant(doc, navigator: ASTNavigator):
    pos = Position(line=20, character=19)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration
