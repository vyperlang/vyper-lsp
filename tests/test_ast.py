from pygls.lsp.types import Position
import pytest

from vyper_lsp.ast import AST


@pytest.fixture
def ast():
    return AST()


def test_get_constants(ast):
    src = """
x: constant(uint256) = 123
y: uint256
z: constant(bool) = True

@external
def __init__():
    self.y = x
        """
    ast.build_ast(src)
    assert ast.get_constants() == ["x", "z"]


def test_get_enums(ast):
    src = """
enum Foo:
    Bar
    Baz
    """
    ast.build_ast(src)
    assert ast.get_enums() == ["Foo"]


def test_get_enum_variants(ast):
    src = """
enum Foo:
    Bar
    Baz
    """
    ast.build_ast(src)
    assert ast.get_enum_variants("Foo") == ["Bar", "Baz"]


def test_get_events(ast):
    src = """
event Foo:
    arg1: indexed(uint256)
    arg2: indexed(address)
    arg3: uint256
    """
    ast.build_ast(src)
    assert ast.get_events() == ["Foo"]


def test_get_structs(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address
    """
    ast.build_ast(src)
    assert ast.get_structs() == ["Foo"]


def test_get_user_defined_types(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address

event FooEvent:
    arg1: indexed(uint256)
    arg2: indexed(address)

enum FooEnum:
    Bar
    Baz
    """
    ast.build_ast(src)
    assert ast.get_user_defined_types() == ["Foo", "FooEvent", "FooEnum"]


def test_get_state_variables(ast):
    src = """
x: uint256
y: address
z: bool
        """
    ast.build_ast(src)
    assert ast.get_state_variables() == ["x", "y", "z"]


def test_get_internal_functions(ast):
    src = """
@internal
def foo():
    pass

@external
def bar():
    pass
        """
    ast.build_ast(src)
    assert ast.get_internal_functions() == ["foo"]


def test_find_nodes_referencing_internal_function(ast):
    src = """
@internal
def foo():
    pass

@external
def bar():
    self.foo()
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_internal_function("foo")
    assert len(references) == 1
    assert (
        references[0].lineno == 8
    )  # line number of self.foo(), counting first newline


def test_find_nodes_referencing_state_variable(ast):
    src = """
x: uint256
y: address
z: bool

@external
def foo():
    self.x = 123
    self.y = msg.sender
    self.z = True
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_state_variable("x")
    assert len(references) == 1
    assert (
        references[0].lineno == 8
    )  # line number of self.x = 123, counting first newline

    references = ast.find_nodes_referencing_state_variable("y")
    assert len(references) == 1
    assert (
        references[0].lineno == 9
    )  # line number of self.y = msg.sender, counting first newline

    references = ast.find_nodes_referencing_state_variable("z")
    assert len(references) == 1
    assert (
        references[0].lineno == 10
    )  # line number of self.z = True, counting first newline


def test_find_nodes_referencing_constant(ast):
    src = """
x: constant(uint256) = 123
y: uint256
z: constant(bool) = True

@external
def foo():
    self.y = x
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_constant("x")
    assert len(references) == 1
    assert (
        references[0].lineno == 8
    )  # line number of self.y = x, counting first newline

    references = ast.find_nodes_referencing_constant("z")
    assert len(references) == 0


def test_find_nodes_referencing_enum(ast):
    src = """
enum Foo:
    Bar
    Baz

@external
def foo():
    x: Foo = Foo.Bar
    y: Foo = Foo.Baz
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_enum("Foo")
    assert len(references) == 4
    assert references[0].lineno == 8  # line number of self.Bar, counting first newline
    assert references[3].lineno == 9  # line number of self.Baz, counting first newline


def test_find_nodes_referencing_enum_variant(ast):
    src = """
enum Foo:
    Bar
    Baz

@external
def foo():
    x: Foo = Foo.Bar
    y: Foo = Foo.Baz
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_enum_variant("Foo", "Bar")
    assert len(references) == 1
    assert references[0].lineno == 8  # line number of self.Bar, counting first newline

    references = ast.find_nodes_referencing_enum_variant("Foo", "Baz")
    assert len(references) == 1
    assert references[0].lineno == 9  # line number of self.Baz, counting first newline


def test_find_nodes_referencing_struct(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address

@external
def foo():
    x: Foo = Foo({bar: 123, baz: msg.sender})
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_struct("Foo")
    assert len(references) == 2
    assert (
        references[0].lineno == 8
    )  # line number of x: Foo = Foo, counting first newline


def test_find_nodes_referencing_symbol(ast: AST):
    src = """
@internal
def foo() -> uint256:
    x: uint256 = 123
    y: uint256 = x
    return y

@external
def bar():
    self.foo()
        """
    ast.build_ast(src)
    functiondef_node = ast.get_internal_function_nodes()[0]
    fn_ast = AST.create_new_instance(functiondef_node)
    references = fn_ast.find_nodes_referencing_symbol("x")
    assert len(references) == 1
    assert (
        references[0].lineno == 5
    )  # line number of y: uint256 = x, counting first newline


def test_get_attributes_for_symbol(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address

enum Bar:
    Baz

@external
def foo():
    x: Foo = Foo({bar: 123, baz: msg.sender})
        """
    ast.build_ast(src)
    assert ast.get_attributes_for_symbol("Foo") == ["bar", "baz"]
    assert ast.get_attributes_for_symbol("Bar") == ["Baz"]


def test_find_function_declaration_node_for_name(ast):
    src = """
@internal
def foo() -> uint256:
    x: uint256 = 123
    y: uint256 = x
    return y

@external
def bar():
    self.foo()
        """
    ast.build_ast(src)
    assert (
        ast.find_function_declaration_node_for_name("foo").lineno == 3
    )  # line number of def foo(), counting first newline


def test_find_state_variable_declaration_node_for_name(ast):
    src = """
x: uint256
y: address
z: bool

@external
def foo():
    self.x = 123
    self.y = msg.sender
    self.z = True
        """
    ast.build_ast(src)
    assert (
        ast.find_state_variable_declaration_node_for_name("x").lineno == 2
    )  # line number of x: uint256, counting first newline
    assert (
        ast.find_state_variable_declaration_node_for_name("y").lineno == 3
    )  # line number of y: address, counting first newline
    assert (
        ast.find_state_variable_declaration_node_for_name("z").lineno == 4
    )  # line number of z: bool, counting first newline


def test_find_type_declaration_node_for_name(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address

enum Bar:
    Baz

@external
def foo():
    x: Foo = Foo({bar: 123, baz: msg.sender})
        """
    ast.build_ast(src)
    assert (
        ast.find_type_declaration_node_for_name("Foo").lineno == 2
    )  # line number of struct Foo, counting first newline
    assert (
        ast.find_type_declaration_node_for_name("Bar").lineno == 6
    )  # line number of enum Bar, counting first newline


def test_find_top_level_node_at_position(ast):
    src = """
x: uint256
y: address
z: bool

enum Foo:
    Bar
    Baz

@external
def foo():
    self.x = 123
    self.y = msg.sender
    self.z = True
        """
    ast.build_ast(src)
    pos: Position = Position(line=13, character=0)
    assert (
        ast.find_top_level_node_at_pos(pos).lineno == 11
    )  # line number of self.x = 123, counting first newline

    pos: Position = Position(line=8, character=0)
    assert (
        ast.find_top_level_node_at_pos(pos).lineno == 6
    )  # line number of enum Foo, counting first newline


def test_find_node_declaring_symbol(ast):
    src = """
x: uint256
y: address

@external
def foo():
    self.x = 123
    self.y = msg.sender
        """
    ast.build_ast(src)
    assert (
        ast.find_node_declaring_symbol("x").lineno == 2
    )  # line number of x: uint256, counting first newline
    assert (
        ast.find_node_declaring_symbol("y").lineno == 3
    )  # line number of y: address, counting first newline
