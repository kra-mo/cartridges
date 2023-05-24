from abc import abstractmethod
from gi.repository import Gio

from src.game import Game


class Manager:
    """Class in charge of handling a post creation action for games.

    * May connect to signals on the game to handle them.
    * May cancel its running tasks on critical error,
    in that case a new cancellable must be generated for new tasks to run.
    """

    run_after: set[type["Manager"]]

    cancellable: Gio.Cancellable
    errors: list[Exception]

    def __init__(self) -> None:
        super().__init__()
        self.cancellable = Gio.Cancellable()
        self.errors = []

    def cancel_tasks(self):
        """Cancel all tasks for this manager"""
        self.cancellable.cancel()

    def reset_cancellable(self):
        """Reset the cancellable for this manager.
        Alreadyn scheduled Tasks will no longer be cancellable."""
        self.cancellable = Gio.Cancellable()

    def report_error(self, error: Exception):
        """Report an error that happened in of run"""
        self.errors.append(error)

    def collect_errors(self) -> list[Exception]:
        """Get the errors produced by the manager and remove them from self.errors"""
        errors = list(self.errors)
        self.errors.clear()
        return errors

    @abstractmethod
    def run(self, game: Game) -> None:
        """Pass the game through the manager.
        May block its thread.
        May not raise exceptions, as they will be silently ignored."""
        pass
