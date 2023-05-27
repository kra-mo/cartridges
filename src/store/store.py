from src import shared
from src.game import Game
from src.store.managers.manager import Manager
from src.store.pipeline import Pipeline


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

    def add_game(self, game: Game, replace=False) -> Pipeline | None:
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
            for path in (
                shared.games_dir / f"{game.game_id}.json",
                shared.covers_dir / f"{game.game_id}.tiff",
                shared.covers_dir / f"{game.game_id}.gif",
            ):
                path.unlink(missing_ok=True)
            return None

        # Run the pipeline for the game
        pipeline = Pipeline(game, self.managers)
        self.games[game.game_id] = game
        self.pipelines[game.game_id] = pipeline
        pipeline.advance()
        return pipeline
