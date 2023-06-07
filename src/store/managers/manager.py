import logging
from abc import abstractmethod
from threading import Lock
from time import sleep
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
    continue_on: set[type[Exception]] = set()
    retry_delay: int = 3
    max_tries: int = 3

    errors: list[Exception]
    errors_lock: Lock = None

    @property
    def name(self):
        return type(self).__name__

    def __init__(self) -> None:
        super().__init__()
        self.errors = []
        self.errors_lock = Lock()

    def report_error(self, error: Exception):
        """Report an error that happened in Manager.process_game"""
        with self.errors_lock:
            self.errors.append(error)

    def collect_errors(self) -> list[Exception]:
        """Get the errors produced by the manager and remove them from self.errors"""
        with self.errors_lock:
            errors = self.errors.copy()
            self.errors.clear()
        return errors

    @abstractmethod
    def manager_logic(self, game: Game, additional_data: dict) -> None:
        """
        Manager specific logic triggered by the run method
        * Implemented by final child classes
        * May block its thread
        * May raise retryable exceptions that will trigger a retry if possible
        * May raise other exceptions that will be reported
        """

    def execute_resilient_manager_logic(
        self, game: Game, additional_data: dict, try_index: int = 0
    ) -> None:
        """Execute the manager logic and handle its errors by reporting them or retrying"""
        try:
            self.manager_logic(game, additional_data)
        except Exception as error:
            logging_args = (
                type(error).__name__,
                self.name,
                f"{game.name} ({game.game_id})",
            )
            if error in self.continue_on:
                # Handle skippable errors (skip silently)
                return
            elif error in self.retryable_on:
                if try_index < self.max_tries:
                    # Handle retryable errors
                    logging.error("Retrying %s in %s for %s", *logging_args)
                    sleep(self.retry_delay)
                    self.execute_resilient_manager_logic(
                        game, additional_data, try_index + 1
                    )
                else:
                    # Handle being out of retries
                    logging.error(
                        "Out of retries dues to %s in %s for %s", *logging_args
                    )
                    self.report_error(error)
            else:
                # Handle unretryable errors
                logging.error(
                    "Unretryable %s in %s for %s", *logging_args, exc_info=error
                )
                self.report_error(error)

    def process_game(
        self, game: Game, additional_data: dict, callback: Callable[["Manager"], Any]
    ) -> None:
        """Pass the game through the manager"""
        self.execute_resilient_manager_logic(game, additional_data)
        callback(self)
