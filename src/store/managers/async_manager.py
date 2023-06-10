from typing import Callable, Any

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

    def process_game(
        self, game: Game, additional_data: dict, callback: Callable[["Manager"], Any]
    ) -> None:
        """Create a task to process the game in a separate thread"""
        task = Task.new(None, self.cancellable, self._task_callback, (callback,))
        task.set_task_data((game, additional_data))
        task.run_in_thread(self._task_thread_func)

    def _task_thread_func(self, _task, _source_object, data, _cancellable):
        """Task thread entry point"""
        game, additional_data, *_rest = data
        self.execute_resilient_manager_logic(game, additional_data)

    def _task_callback(self, _source_object, _result, data):
        """Method run after the task is done"""
        callback, *_rest = data
        callback(self)
