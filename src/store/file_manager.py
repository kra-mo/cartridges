from src.game import Game
from src.store.manager import Manager
from src.store.sgdb_manager import SGDBManager
from src.store.steam_api_manager import SteamAPIManager


class FileManager(Manager):
    """Manager in charge of saving a game to a file"""

    run_after = set((SteamAPIManager, SGDBManager))

    def run(self, game: Game) -> None:
        # TODO make game.save (disk) not trigger game.update (UI)
        game.save()
