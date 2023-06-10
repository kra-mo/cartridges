from pathlib import Path

from src.game import Game
from src.store.managers.manager import Manager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.utils.save_cover import save_cover, resize_cover


class LocalCoverManager(Manager):
    """Manager in charge of adding the local cover image of the game"""

    run_after = (SteamAPIManager,)

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        # Ensure that the cover path is in the additional data
        try:
            image_path: Path = additional_data["local_image_path"]
        except KeyError:
            return
        if not image_path.is_file():
            return
        # Save the image
        save_cover(game.game_id, resize_cover(image_path))
