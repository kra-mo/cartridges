import logging
from typing import Iterable

from gi.repository import GObject

from src.game import Game
from src.store.managers.manager import Manager


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
        parallel = managers - blocking

        # Schedule parallel managers, then run the blocking ones
        for manager in (*parallel, *blocking):
            self.waiting.remove(manager)
            self.running.add(manager)
            manager.process_game(self.game, self.manager_callback)

    def manager_callback(self, manager: Manager) -> None:
        """Method called by a manager when it's done"""
        logging.debug("%s done for %s", manager.name, self.game.game_id)
        self.running.remove(manager)
        self.done.add(manager)
        self.emit("advanced")
        self.advance()

    @GObject.Signal(name="advanced")
    def advanced(self) -> None:
        """Signal emitted when the pipeline has advanced"""
