# pipeline.py
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
from typing import Iterable

from gi.repository import GObject

from cartridges.game import Game
from cartridges.store.managers.manager import Manager


class Pipeline(GObject.Object):
    """Class representing a set of managers for a game"""

    game: Game
    additional_data: dict

    waiting: set[Manager]
    running: set[Manager]
    done: set[Manager]

    def __init__(
        self, game: Game, additional_data: dict, managers: Iterable[Manager]
    ) -> None:
        super().__init__()
        self.game = game
        self.additional_data = additional_data
        self.waiting = set(managers)
        self.running = set()
        self.done = set()

    @property
    def not_done(self) -> set[Manager]:
        """Get the managers that are not done yet"""
        return self.waiting | self.running

    @property
    def is_done(self) -> bool:
        return len(self.waiting) == 0 and len(self.running) == 0

    @property
    def blocked(self) -> set[Manager]:
        """Get the managers that cannot run because their dependencies aren't done"""
        blocked = set()
        for waiting in self.waiting:
            for not_done in self.not_done:
                if waiting == not_done:
                    continue
                if type(not_done) in waiting.run_after:
                    blocked.add(waiting)
        return blocked

    @property
    def ready(self) -> set[Manager]:
        """Get the managers that can be run"""
        return self.waiting - self.blocked

    @property
    def progress(self) -> float:
        """Get the pipeline progress. Should only be a rough idea."""
        n_done = len(self.done)
        n_total = len(self.waiting) + len(self.running) + n_done
        try:
            progress = n_done / n_total
        except ZeroDivisionError:
            progress = 1
        return progress

    def advance(self) -> None:
        """Spawn tasks for managers that are able to run for a game"""

        # Separate blocking / async managers
        managers = self.ready
        blocking = set(filter(lambda manager: manager.blocking, managers))
        parallel = managers - blocking

        # Schedule parallel managers, then run the blocking ones
        for manager in (*parallel, *blocking):
            self.waiting.remove(manager)
            self.running.add(manager)
            manager.process_game(self.game, self.additional_data, self.manager_callback)

    def manager_callback(self, manager: Manager) -> None:
        """Method called by a manager when it's done"""
        logging.debug("%s done for %s", manager.name, self.game.game_id)
        self.running.remove(manager)
        self.done.add(manager)
        self.emit("advanced")
        self.advance()

    @GObject.Signal(name="advanced")
    def advanced(self):  # type: ignore
        """Signal emitted when the pipeline has advanced"""
