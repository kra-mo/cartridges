from requests.exceptions import HTTPError, SSLError

from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.utils.steam import (
    SteamGameNotFoundError,
    SteamAPIHelper,
    SteamNotAGameError,
    SteamRateLimiter,
)


class SteamAPIManager(AsyncManager):
    """Manager in charge of completing a game's data from the Steam API"""

    retryable_on = (HTTPError, SSLError)

    steam_api_helper: SteamAPIHelper = None
    steam_rate_limiter: SteamRateLimiter = None

    def __init__(self) -> None:
        super().__init__()
        self.steam_rate_limiter = SteamRateLimiter()
        self.steam_api_helper = SteamAPIHelper(self.steam_rate_limiter)

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        # Skip non-steam games
        appid = additional_data.get("steam_appid", None)
        if appid is None:
            return
        # Get online metadata
        try:
            online_data = self.steam_api_helper.get_api_data(appid=appid)
        except (SteamNotAGameError, SteamGameNotFoundError):
            game.update_values({"blacklisted": True})
        else:
            game.update_values(online_data)
