import pytest


@pytest.mark.parametrize("ast_with_code", ["struct_code"], indirect=True)
def test_struct_attributes(ast_with_code):
    """Test that struct attributes are correctly identified."""
    # The ast_with_code fixture has loaded struct_code
    ast = ast_with_code

    # Test struct detection
    assert ast.get_structs() == ["Point"]

    # Test struct fields
    assert ast.get_struct_fields("Point") == ["x", "y"]

    # Test references to the struct
    references = ast.find_nodes_referencing_struct("Point")
    assert (
        len(references) >= 3
    )  # Declaration, usage in set_point, return type in get_point


@pytest.mark.parametrize("ast_with_code", ["enum_code"], indirect=True)
def test_enum_attributes(ast_with_code):
    """Test that enum attributes are correctly identified."""
    # The ast_with_code fixture has loaded enum_code
    ast = ast_with_code

    # Test enum detection
    assert ast.get_enums() == ["Color"]

    # Test enum variants
    assert ast.get_enum_variants("Color") == ["RED", "GREEN", "BLUE"]

    # Test references to the enum
    references = ast.find_nodes_referencing_enum("Color")
    assert len(references) >= 2  # Variable declaration and return type in get_color


@pytest.mark.parametrize("ast_with_code", ["function_code"], indirect=True)
def test_function_attributes(ast_with_code):
    """Test that function attributes are correctly identified."""
    # The ast_with_code fixture has loaded function_code
    ast = ast_with_code

    # Test internal function detection
    assert ast.get_internal_functions() == ["_calculate"]

    # Test function references
    references = ast.find_nodes_referencing_internal_function("_calculate")
    assert len(references) == 1  # Referenced in calculate function

    # Test state variable references
    x_refs = ast.find_nodes_referencing_state_variable("x")
    assert len(x_refs) == 1  # Referenced in set_values

    y_refs = ast.find_nodes_referencing_state_variable("y")
    assert len(y_refs) == 1  # Referenced in set_values


@pytest.mark.parametrize(
    "code_fixture_name, expected_types",
    [("struct_code", ["Point"]), ("enum_code", ["Color"]), ("function_code", [])],
)
def test_user_defined_types(request, ast, code_fixture_name, expected_types):
    """Test user-defined types across different code samples."""
    # Load the code from the specified fixture
    code = request.getfixturevalue(code_fixture_name)
    ast.build_ast(code)

    # Verify the user-defined types match expectations
    assert sorted(ast.get_user_defined_types()) == sorted(expected_types)


def test_real_example_file(example_documents, ast):
    """Test using a real example file from the examples directory."""
    # Load the Foo.vy example
    foo_code = example_documents["Foo.vy"]
    ast.build_ast(foo_code)

    # Verify structs
    assert "Bar" in ast.get_structs()
    assert ast.get_struct_fields("Bar") == ["x"]

    # Verify flags
    assert "Roles" in ast.get_enums()
    assert sorted(ast.get_enum_variants("Roles")) == ["ADMIN", "USER"]

    # Verify constants
    assert "FEE" in ast.get_constants()

    # Verify functions
    assert ast.get_internal_functions() == ["bar"]
