from requests import HTTPError

from src.game import Game
from src.store.manager import Manager
from src.utils.steamgriddb import SGDBAuthError, SGDBError, SGDBHelper


class SGDBManager(Manager):
    """Manager in charge of downloading a game's cover from steamgriddb"""

    def run(self, game: Game) -> None:
        try:
            sgdb = SGDBHelper()
            sgdb.conditionaly_update_cover(game)
        except SGDBAuthError as error:
            # If invalid auth, cancel all SGDBManager tasks
            self.cancellable.cancel()
            self.report_error(error)
        except (HTTPError, SGDBError) as error:
            # On other error, just report it
            self.report_error(error)
            pass
