from src.game import Game
from src.store.manager import Manager
from src.utils.task import Task


class Pipeline(set):
    """Class representing a set of Managers for a game"""

    @property
    def blocked_managers(self) -> set(Manager):
        """Get the managers that cannot run because their dependencies aren't done"""
        blocked = set()
        for manager_a in self:
            for manager_b in self:
                if manager_a == manager_b:
                    continue
                if type(manager_b) in manager_a.run_after:
                    blocked.add(manager_a)
        return blocked

    @property
    def startable_managers(self) -> set(Manager):
        """Get the managers that can be run"""
        return self - self.blocked_managers


class Store:
    """Class in charge of handling games being added to the app."""

    managers: set[Manager]
    pipelines: dict[str, Pipeline]
    games: dict[str, Game]

    def __init__(self) -> None:
        self.managers = set()
        self.games = {}
        self.pipelines = {}

    def add_manager(self, manager: Manager):
        """Add a manager class that will run when games are added"""
        self.managers.add(manager)

    def add_game(self, game: Game, replace=False):
        """Add a game to the app if not already there

        :param replace bool: Replace the game if it already exists"""
        if (
            game.game_id in self.games
            and not self.games[game.game_id].removed
            and not replace
        ):
            return
        self.games[game.game_id] = game
        self.pipelines[game.game_id] = Pipeline(self.managers)
        self.advance_pipeline(game)

    def advance_pipeline(self, game: Game):
        """Spawn tasks for managers that are able to run for a game"""
        for manager in self.pipelines[game.game_id].startable_managers:
            data = (manager, game)
            task = Task.new(None, None, self.manager_task_callback, data)
            task.set_task_data(data)
            task.run_in_thread(self.manager_task_thread_func)

    def manager_task_thread_func(self, _task, _source_object, data, _cancellable):
        """Thread function for manager tasks"""
        manager, game, *_rest = data
        manager.run(game)

    def manager_task_callback(self, _source_object, _result, data):
        """Callback function for manager tasks"""
        manager, game, *_rest = data
        self.pipelines[game.game_id].remove(manager)
        self.advance_pipeline(game)
