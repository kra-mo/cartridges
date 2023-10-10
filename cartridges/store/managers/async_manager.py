# async_manager.py
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

from typing import Any, Callable

from gi.repository import Gio

from cartridges.game import Game
from cartridges.store.managers.manager import Manager


class AsyncManager(Manager):
    """Manager that can run asynchronously"""

    blocking = False
    cancellable: Gio.Cancellable = None

    def __init__(self) -> None:
        super().__init__()
        self.cancellable = Gio.Cancellable()

    def cancel_tasks(self):
        """Cancel all tasks for this manager"""
        self.cancellable.cancel()

    def reset_cancellable(self):
        """Reset the cancellable for this manager.
        Already scheduled Tasks will no longer be cancellable."""
        self.cancellable = Gio.Cancellable()

    def process_game(
        self, game: Game, additional_data: dict, callback: Callable[["Manager"], Any]
    ) -> None:
        """Create a task to process the game in a separate thread"""
        task = Gio.Task.new(None, self.cancellable, self._task_callback, (callback,))
        task.run_in_thread(lambda *_: self._task_thread_func((game, additional_data)))

    def _task_thread_func(self, data):
        """Task thread entry point"""
        game, additional_data, *_rest = data
        self.run(game, additional_data)

    def _task_callback(self, _source_object, _result, data):
        """Method run after the task is done"""
        callback, *_rest = data
        callback(self)
