from urllib3.exceptions import SSLError

from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.utils.steamgriddb import HTTPError, SGDBAuthError, SGDBHelper


class SGDBManager(AsyncManager):
    """Manager in charge of downloading a game's cover from steamgriddb"""

    run_after = set((SteamAPIManager,))
    retryable_on = set((HTTPError, SSLError))

    def manager_logic(self, game: Game, _additional_data: tuple) -> None:
        try:
            sgdb = SGDBHelper()
            sgdb.conditionaly_update_cover(game)
        except SGDBAuthError:
            # If invalid auth, cancel all SGDBManager tasks
            self.cancellable.cancel()
            raise
