from src.game import Game
from src.store.managers.format_update_manager import FormatUpdateManager
from src.store.managers.manager import Manager
from src.store.managers.sgdb_manager import SGDBManager
from src.store.managers.steam_api_manager import SteamAPIManager


class FileManager(Manager):
    """Manager in charge of saving a game to a file"""

    run_after = set((SteamAPIManager, SGDBManager, FormatUpdateManager))

    def run(self, game: Game) -> None:
        # TODO make game.save (disk) not trigger game.update (UI)
        game.save()
