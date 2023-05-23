from abc import abstractmethod

from src.game import Game


class Manager:
    """Class in charge of handling a post creation action for games.
    May connect to signals on the game to handle them."""

    run_after: set[type["Manager"]]

    @abstractmethod
    def run(self, game: Game) -> None:
        """Pass the game through the manager.
        May block its thread.
        May not raise exceptions, as they will be silently ignored."""
        pass
