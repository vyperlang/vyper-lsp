import pytest
from pathlib import Path
from typing import Dict, Tuple
from lsprotocol.types import Position, Range
from pygls.workspace import Document

from vyper_lsp.ast import AST


@pytest.fixture
def ast():
    """Basic AST fixture without any source code loaded."""
    return AST()


@pytest.fixture
def vyper_document(tmp_path) -> Tuple[Document, Path]:
    """Create a temporary Vyper document for testing."""
    file_path = tmp_path / "test_contract.vy"
    file_path.touch()
    doc = Document(uri=str(file_path), source="")
    return doc, file_path


@pytest.fixture
def example_documents() -> Dict[str, str]:
    """Return the source code of example documents."""
    examples_dir = Path(__file__).parent.parent / "examples"
    return {
        "Foo.vy": (examples_dir / "Foo.vy").read_text(),
        "LiquidityGauge.vy": (examples_dir / "LiquidityGauge.vy").read_text(),
    }


@pytest.fixture
def struct_code() -> str:
    """Return a simple Vyper contract with a struct definition."""
    return """
struct Point:
    x: uint256
    y: uint256

my_point: Point

@external
def set_point(x: uint256, y: uint256):
    self.my_point = Point(x=x, y=y)

@external
@view
def get_point() -> Point:
    return self.my_point
"""


@pytest.fixture
def enum_code() -> str:
    """Return a simple Vyper contract with an enum definition."""
    return """
flag Color:
    RED
    GREEN
    BLUE

my_color: Color

@external
def set_color(color: Color):
    self.my_color = color

@external
@view
def get_color() -> Color:
    return self.my_color
"""


@pytest.fixture
def function_code() -> str:
    """Return a simple Vyper contract with internal and external functions."""
    return """
x: uint256
y: uint256

@internal
def _calculate(a: uint256, b: uint256) -> uint256:
    return a + b

@external
def calculate(a: uint256, b: uint256) -> uint256:
    return self._calculate(a, b)

@external
def set_values(a: uint256, b: uint256):
    self.x = a
    self.y = b
"""


@pytest.fixture
def position(line: int = 0, character: int = 0) -> Position:
    """Create a Position instance for testing."""
    return Position(line=line, character=character)


@pytest.fixture
def range_fixture(
    start_line: int = 0, start_char: int = 0, end_line: int = 0, end_char: int = 0
) -> Range:
    """Create a Range instance for testing."""
    return Range(
        start=Position(line=start_line, character=start_char),
        end=Position(line=end_line, character=end_char),
    )


@pytest.fixture
def ast_with_code(request, ast):
    """
    Parameterized fixture that loads code into an AST instance.

    Usage:
    @pytest.mark.parametrize('ast_with_code', ['struct_code', 'enum_code', 'function_code'], indirect=True)
    def test_something(ast_with_code):
        # ast_with_code has the specified code loaded
        ...
    """
    if hasattr(request, "param"):
        code_fixture = request.getfixturevalue(request.param)
        ast.build_ast(code_fixture)
    return ast
