import time
from vyper_lsp.debounce import Debouncer  # Import Debouncer from your module


def test_debounce():
    result = []

    def test_function(arg):
        result.append(arg)

    debouncer = Debouncer(wait=0.5)
    debounced_func = debouncer.debounce(test_function)

    debounced_func("first call")
    time.sleep(0.2)  # Sleep for less than the debounce period
    debounced_func("second call")
    time.sleep(
        0.6
    )  # Sleep for more than the debounce period to allow the function to execute

    assert result == ["second call"]
