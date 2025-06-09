import pytest
from pathlib import Path
from vyper_lsp.ast import AST
from pygls.workspace import Document
from vyper.compiler.input_bundle import FilesystemInputBundle
from vyper_lsp.handlers.completion import CompletionHandler
from vyper.ast import nodes


@pytest.fixture
def multifile_setup(tmp_path):
    """Set up a multi-file project structure for testing"""
    # Create library file
    lib_content = """
counter: uint256

@internal
def increment_counter():
    self.counter += 1

@external
def get_count() -> uint256:
    return self.counter
"""
    
    # Create main contract that imports the library
    main_content = """
import lib

initializes: lib

@external
def increment():
    lib.increment_counter()

@external  
def get_counter() -> uint256:
    return lib.counter
"""
    
    # Write files
    (tmp_path / "lib.vy").write_text(lib_content)
    (tmp_path / "main.vy").write_text(main_content)
    
    return tmp_path, main_content


def test_multifile_import_resolution(multifile_setup):
    """Test that imports are properly resolved in multi-file projects"""
    tmp_path, main_content = multifile_setup
    
    # Create document
    doc = Document(
        uri=f"file://{tmp_path.absolute()}/main.vy",
        source=main_content
    )
    
    # Create AST instance
    ast = AST()
    
    # Build AST (this should handle imports)
    diagnostics = ast.build_ast(doc)
    
    # Should have no errors
    assert diagnostics == []
    
    # Check if imports were loaded
    assert ast.imports is not None
    assert "lib" in ast.imports
    
    # Check imported module has expected content
    lib_module = ast.imports["lib"]
    assert hasattr(lib_module, "functions")
    assert "increment_counter" in lib_module.functions
    assert "get_count" in lib_module.functions
    assert hasattr(lib_module, "variables")
    assert "counter" in lib_module.variables


def test_multifile_completions(multifile_setup):
    """Test that completions work for imported modules"""
    tmp_path, main_content = multifile_setup
    
    # Create document
    doc = Document(
        uri=f"file://{tmp_path.absolute()}/main.vy",
        source=main_content
    )
    
    # Create AST instance and build
    ast = AST()
    ast.build_ast(doc)
    
    # Create completion handler
    handler = CompletionHandler(ast)
    
    # Test completions in function context (should show internal functions)
    function_node = nodes.FunctionDef()
    completions = handler._dot_completions_for_module("lib", top_level_node=function_node)
    completion_labels = [c.label for c in completions]
    
    assert "increment_counter" in completion_labels  # internal function
    assert "counter" in completion_labels  # variable
    assert "get_count" not in completion_labels  # external function not shown in function context
    
    # Test completions in exports context (should show external functions)
    completions = handler._dot_completions_for_module("lib", line="exports: lib.get_count")
    completion_labels = [c.label for c in completions]
    
    assert "get_count" in completion_labels  # external function
    assert "counter" in completion_labels  # variable
    assert "increment_counter" not in completion_labels  # internal function not shown in exports