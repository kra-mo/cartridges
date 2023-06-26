# sgdb_manager.py
#
# Copyright 2023 Geoffrey Coulaud
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from json import JSONDecodeError

from requests.exceptions import HTTPError, SSLError

from src.errors.friendly_error import FriendlyError
from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.store.managers.local_cover_manager import LocalCoverManager
from src.store.managers.online_cover_manager import OnlineCoverManager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.utils.steamgriddb import SGDBAuthError, SGDBHelper


class SGDBManager(AsyncManager):
    """Manager in charge of downloading a game's cover from steamgriddb"""

    run_after = (SteamAPIManager, LocalCoverManager, OnlineCoverManager)
    retryable_on = (HTTPError, SSLError, ConnectionError, JSONDecodeError)

    def manager_logic(self, game: Game, _additional_data: dict) -> None:
        try:
            sgdb = SGDBHelper()
            sgdb.conditionaly_update_cover(game)
        except SGDBAuthError as error:
            # If invalid auth, cancel all SGDBManager tasks
            self.cancellable.cancel()
            raise FriendlyError(
                _("Couldn't authenticate SteamGridDB"),
                _("Verify your API key in preferences"),
            ) from error
