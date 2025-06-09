from lsprotocol.types import Position
from pygls.workspace import Document

from vyper_lsp.ast import AST


def test_document_fixture(vyper_document, struct_code):
    """Test that the document fixture can be used to create a document with source code."""
    doc, file_path = vyper_document

    # Update the document with the struct code
    doc = Document(uri=str(file_path), source=struct_code)

    # Use the document to test AST functionality
    ast = AST()
    diagnostics = ast.build_ast(doc)

    # Verify no diagnostics were reported
    assert len(diagnostics) == 0

    # Verify the expected structs were found
    assert ast.get_structs() == ["Point"]


def test_document_diagnostics(vyper_document):
    """Test that malformed code produces diagnostics."""
    doc, file_path = vyper_document

    # Invalid Vyper code with a syntax error
    invalid_code = """
struct Point:
    x: uint256
    y uint256  # Missing colon

@external
def set_point(x: uint256, y: uint256):
    self.my_point = Point(x=x, y=y)
"""

    # Update the document with the invalid code
    doc = Document(uri=str(file_path), source=invalid_code)

    # Use the document to test AST functionality
    ast = AST()
    diagnostics = ast.build_ast(doc)

    # Verify diagnostics were reported
    assert len(diagnostics) > 0


def test_example_document_loading(example_documents, ast):
    """Test loading different example documents."""
    # Test with Foo.vy which we know is compatible
    ast.build_ast(example_documents["Foo.vy"])
    assert "Bar" in ast.get_structs()
    assert "Roles" in ast.get_enums()

    # Note: We're not testing LiquidityGauge.vy as it may have version
    # compatibility issues with the current Vyper version


def test_find_top_level_node_with_position(vyper_document, function_code):
    """Test finding a top-level node at a given position."""
    doc, file_path = vyper_document

    # Update the document with the function code
    doc = Document(uri=str(file_path), source=function_code)

    # Use the document to test AST functionality
    ast = AST()
    ast.build_ast(doc)

    # Position in the _calculate function (internal)
    internal_pos = Position(line=6, character=5)  # Line with "return a + b"
    internal_node = ast.find_top_level_node_at_pos(internal_pos)
    assert internal_node is not None
    assert hasattr(internal_node, "name")
    assert internal_node.name == "_calculate"

    # Position in the calculate function (external)
    external_pos = Position(
        line=10, character=5
    )  # Line with "return self._calculate(a, b)"
    external_node = ast.find_top_level_node_at_pos(external_pos)
    assert external_node is not None
    assert hasattr(external_node, "name")
    assert external_node.name == "calculate"
