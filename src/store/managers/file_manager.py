from src.game import Game
from src.store.managers.manager import Manager
from src.store.managers.steam_api_manager import SteamAPIManager


class FileManager(Manager):
    """Manager in charge of saving a game to a file"""

    run_after = set((SteamAPIManager,))

    def run(self, game: Game) -> None:
        game.save()
