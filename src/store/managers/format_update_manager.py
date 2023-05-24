from src.store.managers.manager import Manager
from src.game import Game


class FormatUpdateManager(Manager):
    """Class in charge of migrating a game from an older format"""

    def v1_5_to_v2_0(self, game: Game) -> None:
        """Convert a game from v1.5 format to v2.0 format"""
        if game.blacklisted is None:
            game.blacklisted = False
        if game.removed is None:
            game.removed = False
        game.version = 2.0

    def run(self, game: Game) -> None:
        if game.version is None:
            self.v1_5_to_v2_0(game)
        game.save()
