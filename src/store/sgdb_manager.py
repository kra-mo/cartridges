from src.store.manager import Manager
from src.game import Game
from src.utils.steamgriddb import SGDBHelper


class SGDBManager(Manager):
    """Manager in charge of downloading a game's cover from steamgriddb"""

    def run(self, game: Game) -> None:
        # TODO
        pass
