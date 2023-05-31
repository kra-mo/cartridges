import logging
from abc import abstractmethod
from typing import Any, Callable

from src.game import Game


class Manager:
    """Class in charge of handling a post creation action for games.

    * May connect to signals on the game to handle them.
    * May cancel its running tasks on critical error,
    in that case a new cancellable must be generated for new tasks to run.
    * May be retried on some specific error types
    """

    run_after: set[type["Manager"]] = set()
    blocking: bool = True
    retryable_on: set[type[Exception]] = set()
    max_tries: int = 3

    errors: list[Exception]

    @property
    def name(self):
        return type(self).__name__

    def __init__(self) -> None:
        super().__init__()
        self.errors = []

    def report_error(self, error: Exception):
        """Report an error that happened in Manager.run"""
        self.errors.append(error)

    def collect_errors(self) -> list[Exception]:
        """Get the errors produced by the manager and remove them from self.errors"""
        errors = list(self.errors)
        self.errors.clear()
        return errors

    @abstractmethod
    def final_run(self, game: Game) -> None:
        """
        Manager specific logic triggered by the run method
        * Implemented by final child classes
        * Called by the run method, not used directly
        * May block its thread
        * May raise retryable exceptions that will be be retried if possible
        * May raise other exceptions that will be reported
        """

    def run(self, game: Game, callback: Callable[["Manager"], Any]) -> None:
        """
        Pass the game through the manager
        * Public method called by a pipeline
        * In charge of calling the final_run method and handling its errors
        """

        for remaining_tries in range(self.max_tries, -1, -1):
            try:
                self.final_run(game, self.max_tries)
            except Exception as error:
                if type(error) in self.retryable_on:
                    # Handle unretryable errors
                    logging.error("Unretryable error in %s", self.name, exc_info=error)
                    self.report_error(error)
                    break
                elif remaining_tries == 0:
                    # Handle being out of retries
                    logging.error("Out of retries in %s", self.name, exc_info=error)
                    self.report_error(error)
                    break
                else:
                    # Retry
                    logging.debug("Retrying %s (%s)", self.name, type(error).__name__)
                    continue

        callback(self)
