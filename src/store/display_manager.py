import src.shared as shared
from src.game import Game
from src.store.manager import Manager
from src.store.sgdb_manager import SGDBManager
from src.store.steam_api_manager import SteamAPIManager


class DisplayManager(Manager):
    """Manager in charge of adding a game to the UI"""

    run_after = set((SteamAPIManager, SGDBManager))

    def run(self, game: Game) -> None:
        # TODO decouple a game from its widget
        shared.win.games[game.game_id] = game
        game.update()
