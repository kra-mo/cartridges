from urllib3.exceptions import SSLError

import requests
from requests import HTTPError

from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.store.managers.local_cover_manager import LocalCoverManager


class ItchCoverManager(AsyncManager):
    """Manager in charge of downloading the game's cover from itch.io"""

    run_after = set((LocalCoverManager,))
    retryable_on = set((HTTPError, SSLError))

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        # TODO move itch cover logic here
        pass
