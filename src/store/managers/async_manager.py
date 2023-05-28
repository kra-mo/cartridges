from typing import Callable

from gi.repository import Gio

from src.game import Game
from src.store.managers.manager import Manager
from src.utils.task import Task


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

    def run(self, game: Game, callback: Callable) -> None:
        task = Task.new(self, self.cancellable, self._task_callback, (callback,))
        task.set_task_data((game,))
        task.run_in_thread(self._task_thread_func)

    def _task_thread_func(self, _task, _source_object, data, cancellable):
        """Task thread entry point"""
        game, *_rest = data
        self.final_run(game)

    def _task_callback(self, _source_object, _result, data):
        """Method run after the async task is done"""
        _game, callback, *_rest = data
        callback(self)
