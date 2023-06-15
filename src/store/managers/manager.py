import logging
from abc import abstractmethod
from threading import Lock
from time import sleep
from typing import Any, Callable, Container

from src.game import Game


class Manager:
    """Class in charge of handling a post creation action for games.

    * May connect to signals on the game to handle them.
    * May cancel its running tasks on critical error,
    in that case a new cancellable must be generated for new tasks to run.
    * May be retried on some specific error types
    """

    run_after: Container[type["Manager"]] = tuple()
    blocking: bool = True

    retryable_on: Container[type[Exception]] = tuple()
    continue_on: Container[type[Exception]] = tuple()
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

    def execute_resilient_manager_logic(self, game: Game, additional_data: dict):
        """Handle errors (retry, ignore or raise) that occur the manager logic"""

        # Keep track of the number of tries
        tries = 1

        def handle_error(error: Exception):
            nonlocal tries

            log_args = (
                type(error).__name__,
                self.name,
                f"{game.name} ({game.game_id})",
            )

            out_of_retries_format = "Out of retries dues to %s in %s for %s"
            retrying_format = "Retrying %s in %s for %s"
            unretryable_format = "Unretryable %s in %s for %s"

            if error in self.continue_on:
                # Handle skippable errors (skip silently)
                return

            if error in self.retryable_on:
                if tries > self.max_tries:
                    # Handle being out of retries
                    logging.error(out_of_retries_format, *log_args)
                    self.report_error(error)
                else:
                    # Handle retryable errors
                    logging.error(retrying_format, *log_args)
                    sleep(self.retry_delay)
                    tries += 1
                    try_manager_logic()

            else:
                # Handle unretryable errors
                logging.error(unretryable_format, *log_args, exc_info=error)
                self.report_error(error)

        def try_manager_logic():
            try:
                self.manager_logic(game, additional_data)
            except Exception as error:  # pylint: disable=broad-exception-caught
                handle_error(error)

        try_manager_logic()

    def process_game(
        self, game: Game, additional_data: dict, callback: Callable[["Manager"], Any]
    ) -> None:
        """Pass the game through the manager"""
        # TODO: connect to signals here
        self.execute_resilient_manager_logic(game, additional_data)
        callback(self)
