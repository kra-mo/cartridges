from threading import Lock


class ErrorProducer:
    """
    A mixin for objects that produce errors.

    Specifies the report_error and collect_errors methods in a thread-safe manner.
    """

    errors: list[Exception]
    errors_lock: Lock

    def __init__(self) -> None:
        self.errors = []
        self.errors_lock = Lock()

    def report_error(self, error: Exception) -> None:
        """Report an error"""
        with self.errors_lock:
            self.errors.append(error)

    def collect_errors(self) -> list[Exception]:
        """Collect and remove the errors produced by the object"""
        with self.errors_lock:
            errors = self.errors.copy()
            self.errors.clear()
        return errors
