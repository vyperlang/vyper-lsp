import threading


class Debouncer:
    def __init__(self, wait):
        self.wait = wait
        self.timer = None
        self.lock = threading.Lock()

    def debounce(self, func):
        def debounced(*args, **kwargs):
            with self.lock:
                if self.timer is not None:
                    self.timer.cancel()  # Cancel the existing timer if there is one
                # Create a new timer that will call func with the latest arguments
                self.timer = threading.Timer(self.wait, lambda: func(*args, **kwargs))
                self.timer.start()

        return debounced
