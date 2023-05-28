from requests import HTTPError, JSONDecodeError

from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.utils.steam import SteamGameNotFoundError, SteamHelper, SteamNotAGameError


class SteamAPIManager(AsyncManager):
    """Manager in charge of completing a game's data from the Steam API"""

    def final_run(self, game: Game) -> None:
        # Skip non-steam games
        if not game.source.startswith("steam_"):
            return

        # Get online metadata
        appid = str(game.game_id).split("_")[-1]
        steam = SteamHelper()
        try:
            online_data = steam.get_api_data(appid=appid)
        except (HTTPError, JSONDecodeError) as error:
            # On minor error, just report it
            self.report_error(error)
        except (SteamNotAGameError, SteamGameNotFoundError):
            game.update_values({"blacklisted": True})
        else:
            game.update_values(online_data)
