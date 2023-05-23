from src.store.manager import Manager
from src.game import Game
from src.utils.steam import SteamHelper


class SteamAPIManager(Manager):
    """Manager in charge of completing a game's data from the Steam API"""

    def run(self, game: Game) -> None:
        # TODO
        pass
