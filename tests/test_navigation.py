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
    assert declaration and declaration.start.line == 16


def test_find_declaration_struct(doc, navigator: ASTNavigator):
    pos = Position(line=22, character=7)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 6

    pos = Position(line=22, character=14)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 6


def test_find_declaration_enum(doc, navigator: ASTNavigator):
    pos = Position(line=25, character=7)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 9


def test_find_declaration_enum_variant(doc, navigator: ASTNavigator):
    # TODO: this currently jumps to the enum declaration, not the variant
    pos = Position(line=25, character=25)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 9


def test_find_declaration_event(doc, navigator: ASTNavigator):
    pos = Position(line=24, character=10)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 2


def test_find_declaration_function(doc, navigator: ASTNavigator):
    pos = Position(line=35, character=17)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 40


def test_find_declaration_storage_var(doc, navigator: ASTNavigator):
    pos = Position(line=26, character=9)
    declaration = navigator.find_declaration(doc, pos)
    assert declaration and declaration.start.line == 13
