from src import shared
from src.game import Game
from src.store.managers.manager import Manager
from src.store.managers.sgdb_manager import SGDBManager
from src.store.managers.steam_api_manager import SteamAPIManager


class DisplayManager(Manager):
    """Manager in charge of adding a game to the UI"""

    run_after = set((SteamAPIManager, SGDBManager))

    def run(self, game: Game) -> None:
        # TODO decouple a game from its widget
        shared.win.games[game.game_id] = game
        game.update()
