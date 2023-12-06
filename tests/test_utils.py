from vyper_lsp import utils


def test_get_word_at_cursor():
    text = "self.foo = 123"
    assert utils.get_word_at_cursor(text, 0) == "self"
    assert utils.get_word_at_cursor(text, 1) == "self"
    assert utils.get_word_at_cursor(text, 5) == "foo"
    assert utils.get_word_at_cursor(text, 12) == "123"

    text = "foo_bar = 123"
    assert utils.get_word_at_cursor(text, 0) == "foo_bar"
    assert utils.get_word_at_cursor(text, 4) == "foo_bar"


def test_get_expression_at_cursor():
    text = "self.foo = 123"
    assert utils.get_expression_at_cursor(text, 0) == "self.foo"
    assert utils.get_expression_at_cursor(text, 1) == "self.foo"
    assert utils.get_expression_at_cursor(text, 5) == "self.foo"
    assert utils.get_expression_at_cursor(text, 12) == "123"

    text = "foo_bar = self.baz (1,2,3)"
    assert utils.get_expression_at_cursor(text, 0) == "foo_bar"
    assert utils.get_expression_at_cursor(text, 4) == "foo_bar"
    assert utils.get_expression_at_cursor(text, 21) == "self.baz (1,2,3)"


def test_get_internal_fn_name_at_cursor():
    text = "self.foo = 123"
    assert utils.get_internal_fn_name_at_cursor(text, 0) is None
    assert utils.get_internal_fn_name_at_cursor(text, 1) is None
    assert utils.get_internal_fn_name_at_cursor(text, 5) is None
    assert utils.get_internal_fn_name_at_cursor(text, 12) is None

    text = "foo_bar = self.baz (1,2,3)"
    assert utils.get_internal_fn_name_at_cursor(text, 0) is None
    assert utils.get_internal_fn_name_at_cursor(text, 4) is None
    assert utils.get_internal_fn_name_at_cursor(text, 21) == "baz"

    text = "self.foo(self.bar())"
    assert utils.get_internal_fn_name_at_cursor(text, 7) == "foo"
