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
    def manager_logic(self, game: Game) -> None:
        """
        Manager specific logic triggered by the run method
        * Implemented by final child classes
        * May block its thread
        * May raise retryable exceptions that will trigger a retry if possible
        * May raise other exceptions that will be reported
        """

    def execute_resilient_manager_logic(self, game: Game) -> None:
        """Execute the manager logic and handle its errors by reporting them or retrying"""
        for remaining_tries in range(self.max_tries, -1, -1):
            try:
                self.manager_logic(game)
            except Exception as error:
                # Handle unretryable errors
                log_args = (type(error).__name__, self.name, game.game_id)
                if type(error) in self.retryable_on:
                    logging.error("Unretryable %s in %s for %s", *log_args)
                    self.report_error(error)
                    break
                # Handle being out of retries
                elif remaining_tries == 0:
                    logging.error("Too many retries due to %s in %s for %s", *log_args)
                    self.report_error(error)
                    break
                # Retry
                else:
                    logging.debug("Retry caused by %s in %s for %s", *log_args)
                    continue

    def process_game(self, game: Game, callback: Callable[["Manager"], Any]) -> None:
        """Pass the game through the manager"""
        self.execute_resilient_manager_logic(game, tries=0)
        callback(self)
