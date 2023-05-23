import src.shared as shared
from src.store.manager import Manager
from src.game import Game


class DisplayManager(Manager):
    """Manager in charge of adding a game to the UI"""

    def run(self, game: Game) -> None:
        # TODO decouple a game from its widget
        shared.win.games[game.game_id] = game
        game.update()
