import pytest

from vyper_lsp.ast import AST


@pytest.fixture
def ast():
    return AST()
