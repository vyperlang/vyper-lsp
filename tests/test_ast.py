from lsprotocol.types import Position
from vyper_lsp.ast import AST


def test_get_constants(ast):
    src = """
x: constant(uint256) = 123
y: uint256
z: constant(bool) = True

@deploy
def __init__():
    self.y = x
        """
    ast.build_ast(src)
    assert ast.get_constants() == ["x", "z"]


def test_get_flags(ast):
    src = """
flag Foo:
    Bar
    Baz
    """
    ast.build_ast(src)
    assert ast.get_enums() == ["Foo"]


def test_get_flag_variants(ast):
    src = """
flag Foo:
    Bar
    Baz
    """
    ast.build_ast(src)
    assert ast.get_enum_variants("Foo") == ["Bar", "Baz"]
    assert ast.get_enum_variants("Bar") == []


def test_get_struct_fields(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address
    """
    ast.build_ast(src)
    assert ast.get_struct_fields("Foo") == ["bar", "baz"]
    assert ast.get_struct_fields("Bar") == []


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

flag FooFlag:
    Bar
    Baz
    """
    ast.build_ast(src)
    assert ast.get_user_defined_types() == ["Foo", "FooFlag"]


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


def test_find_nodes_referencing_constant_folded(ast):
    src = """
x: constant(uint256) = 10 ** 2
y: uint256

@external
def foo():
    self.y = x
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_constant("x")
    assert len(references) == 1
    assert (
        references[0].lineno == 7
    )  # line number of self.y = x, counting first newline


def test_find_nodes_referencing_flag(ast):
    src = """
flag Foo:
    Bar
    Baz

@external
def foo():
    x: Foo = Foo.Bar
    y: Foo = Foo.Baz

@external
def bar() -> Foo:
    return Foo.Bar
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_enum("Foo")
    assert len(references) == 6
    assert references[0].lineno == 8  # line number of self.Bar, counting first newline
    assert references[3].lineno == 9  # line number of self.Baz, counting first newline


def test_find_nodes_referencing_flag_variant(ast):
    src = """
flag Foo:
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
    x: Foo = Foo(bar=123, baz=msg.sender)

@external
def bar() -> Foo:
    return Foo(bar=123, baz=msg.sender)
        """
    ast.build_ast(src)
    references = ast.find_nodes_referencing_struct("Foo")
    assert len(references) == 4
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
    fn_ast = AST.from_node(functiondef_node)
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

flag Bar:
    Baz

@external
def foo():
    x: Foo = Foo(bar=123, baz=msg.sender)
        """
    ast.build_ast(src)
    assert ast.get_attributes_for_symbol("Foo") == ["bar", "baz"]
    assert ast.get_attributes_for_symbol("Bar") == ["Baz"]
    assert ast.get_attributes_for_symbol("Baz") == []


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
    assert ast.find_function_declaration_node_for_name("baz") is None


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
    assert ast.find_state_variable_declaration_node_for_name("baz") is None


def test_find_type_declaration_node_for_name(ast):
    src = """
struct Foo:
    bar: uint256
    baz: address

flag Bar:
    Baz

@external
def foo():
    x: Foo = Foo(bar=123, baz=msg.sender)
        """
    ast.build_ast(src)
    assert (
        ast.find_type_declaration_node_for_name("Foo").lineno == 2
    )  # line number of struct Foo, counting first newline
    assert (
        ast.find_type_declaration_node_for_name("Bar").lineno == 6
    )  # line number of flag Bar, counting first newline
    assert (
        ast.find_type_declaration_node_for_name("Baz").lineno == 7
    )  # line number of Baz, counting first newline
    assert ast.find_type_declaration_node_for_name("baz") is None


def test_find_top_level_node_at_position(ast):
    src = """
x: uint256
y: address
z: bool

flag Foo:
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
    )  # line number of flag Foo, counting first newline


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


def test_ast_no_data_returns_empty_and_none(ast: AST):
    ast.ast_data = None
    ast.ast_data_annotated = None

    assert ast.get_constants() == []
    assert ast.get_enums() == []
    assert ast.get_enum_variants("Foo") == []
    assert ast.get_events() == []
    assert ast.get_structs() == []
    assert ast.get_user_defined_types() == []
    assert ast.get_state_variables() == []
    assert ast.get_internal_functions() == []
    assert ast.get_struct_fields("Foo") == []
    assert ast.get_internal_function_nodes() == []
    assert ast.find_nodes_referencing_internal_function("foo") == []
    assert ast.find_nodes_referencing_state_variable("x") == []
    assert ast.find_nodes_referencing_constant("x") == []
    assert ast.find_nodes_referencing_enum("Foo") == []
    assert ast.find_nodes_referencing_enum_variant("Foo", "Bar") == []
    assert ast.find_nodes_referencing_struct("Foo") == []
    assert ast.find_nodes_referencing_symbol("x") == []
    assert ast.get_attributes_for_symbol("Foo") == []
    assert ast.find_function_declaration_node_for_name("foo") is None
    assert ast.find_state_variable_declaration_node_for_name("x") is None
    assert ast.find_type_declaration_node_for_name("Foo") is None
    assert ast.find_top_level_node_at_pos(Position(line=0, character=0)) is None
    assert ast.find_node_declaring_symbol("x") is None
