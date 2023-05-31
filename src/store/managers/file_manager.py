from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.store.managers.steam_api_manager import SteamAPIManager


class FileManager(AsyncManager):
    """Manager in charge of saving a game to a file"""

    run_after = set((SteamAPIManager,))

    def manager_logic(self, game: Game) -> None:
        game.save()
