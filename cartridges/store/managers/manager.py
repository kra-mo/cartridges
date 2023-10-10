# manager.py
#
# Copyright 2023 Geoffrey Coulaud
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from abc import abstractmethod
from time import sleep
from typing import Any, Callable, Container

from cartridges.errors.error_producer import ErrorProducer
from cartridges.errors.friendly_error import FriendlyError
from cartridges.game import Game


class Manager(ErrorProducer):
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
    signals: Container[type[str]] = set()
    retry_delay: int = 3
    max_tries: int = 3

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    def main(self, game: Game, additional_data: dict) -> None:
        """
        Manager specific logic triggered by the run method
        * Implemented by final child classes
        * May block its thread
        * May raise retryable exceptions that will trigger a retry if possible
        * May raise other exceptions that will be reported
        """

    def run(self, game: Game, additional_data: dict) -> None:
        """Handle errors (retry, ignore or raise) that occur in the manager logic"""

        # Keep track of the number of tries
        tries = 1

        def handle_error(error: Exception) -> None:
            nonlocal tries

            # If FriendlyError, handle its cause instead
            base_error = error
            if isinstance(error, FriendlyError):
                error = error.__cause__

            log_args = (
                type(error).__name__,
                self.name,
                f"{game.name} ({game.game_id})",
            )

            out_of_retries_format = "Out of retries dues to %s in %s for %s"
            retrying_format = "Retrying %s in %s for %s"
            unretryable_format = "Unretryable %s in %s for %s"

            if type(error) in self.continue_on:
                # Handle skippable errors (skip silently)
                return

            if type(error) in self.retryable_on:
                if tries > self.max_tries:
                    # Handle being out of retries
                    logging.error(out_of_retries_format, *log_args)
                    self.report_error(base_error)
                else:
                    # Handle retryable errors
                    logging.error(retrying_format, *log_args)
                    sleep(self.retry_delay)
                    tries += 1
                    try_manager_logic()

            else:
                # Handle unretryable errors
                logging.error(unretryable_format, *log_args, exc_info=error)
                self.report_error(base_error)

        def try_manager_logic() -> None:
            try:
                self.main(game, additional_data)
            except Exception as error:  # pylint: disable=broad-exception-caught
                handle_error(error)

        try_manager_logic()

    def process_game(
        self, game: Game, additional_data: dict, callback: Callable[["Manager"], Any]
    ) -> None:
        """Pass the game through the manager"""
        self.run(game, additional_data)
        callback(self)
