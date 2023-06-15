from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.store.managers.manager import Manager
from src.store.pipeline import Pipeline


class Store:
    """Class in charge of handling games being added to the app."""

    managers: dict[type[Manager], Manager]
    pipelines: dict[str, Pipeline]
    games: dict[str, Game]

    def __init__(self) -> None:
        self.managers = {}
        self.games = {}
        self.pipelines = {}

    def add_manager(self, manager: Manager, in_pipeline=True):
        """Add a manager that will run when games are added"""
        self.managers[type(manager)] = [manager, in_pipeline]

    def manager_to_pipeline(self, manager_type: type[Manager]):
        self.managers[manager_type][1] = True

    def add_game(
        self, game: Game, additional_data: dict, replace=False
    ) -> Pipeline | None:
        """Add a game to the app if not already there

        :param replace bool: Replace the game if it already exists
        """

        # Ignore games from a newer spec version
        if game.version > shared.SPEC_VERSION:
            return None

        # Ignore games that are already there
        if (
            game.game_id in self.games
            and not self.games[game.game_id].removed
            and not replace
        ):
            return None

        # Cleanup removed games
        if game.removed:
            # TODO: come back to this later
            for path in (
                shared.games_dir / f"{game.game_id}.json",
                shared.covers_dir / f"{game.game_id}.tiff",
                shared.covers_dir / f"{game.game_id}.gif",
            ):
                path.unlink(missing_ok=True)
            return None

        # Connect signals
        for manager, _in_pipeline in self.managers.values():
            for signal in manager.signals:
                game.connect(signal, manager.execute_resilient_manager_logic)

        # Run the pipeline for the game
        pipeline = Pipeline(
            game,
            additional_data,
            (manager[0] for manager in self.managers.values() if manager[1]),
        )
        self.games[game.game_id] = game
        self.pipelines[game.game_id] = pipeline
        pipeline.advance()
        return pipeline
