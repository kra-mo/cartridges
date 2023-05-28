from typing import Iterable

from gi.repository import GObject

from src.game import Game
from src.store.managers.manager import Manager
from src.utils.task import Task


class Pipeline(GObject.Object):
    """Class representing a set of managers for a game"""

    game: Game

    waiting: set[Manager]
    running: set[Manager]
    done: set[Manager]

    def __init__(self, game: Game, managers: Iterable[Manager]) -> None:
        super().__init__()
        self.game = game
        self.waiting = set(managers)
        self.running = set()
        self.done = set()

    @property
    def not_done(self) -> set[Manager]:
        """Get the managers that are not done yet"""
        return self.waiting | self.running

    @property
    def is_done(self) -> bool:
        return len(self.not_done) == 0

    @property
    def blocked(self) -> set[Manager]:
        """Get the managers that cannot run because their dependencies aren't done"""
        blocked = set()
        for manager_a in self.waiting:
            for manager_b in self.not_done:
                if manager_a == manager_b:
                    continue
                if type(manager_b) in manager_a.run_after:
                    blocked.add(manager_a)
        return blocked

    @property
    def ready(self) -> set[Manager]:
        """Get the managers that can be run"""
        return self.waiting - self.blocked

    def advance(self):
        """Spawn tasks for managers that are able to run for a game"""

        # Separate blocking / async managers
        managers = self.ready
        blocking = set(filter(lambda manager: manager.blocking, managers))
        parallel = managers - parallel

        # Schedule parallel managers, then run the blocking ones
        for manager in (*parallel, *blocking):
            manager.run(self.game)

    @GObject.Signal(name="manager-started", arg_types=(object,))
    def manager_started(self, manager: Manager) -> None:
        """Signal emitted when a manager is started"""
        pass

    @GObject.Signal(name="manager-done", arg_types=(object,))
    def manager_done(self, manager: Manager) -> None:
        """Signal emitted when a manager is done"""
        pass

    def on_manager_started(self, manager: Manager) -> None:
        self.emit("manager-started", manager)

    def on_manager_done(self, manager: Manager) -> None:
        self.emit("manager-done", manager)
        self.advance()
