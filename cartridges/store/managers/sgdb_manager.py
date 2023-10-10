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

from cartridges.errors.friendly_error import FriendlyError
from cartridges.game import Game
from cartridges.store.managers.async_manager import AsyncManager
from cartridges.store.managers.cover_manager import CoverManager
from cartridges.store.managers.steam_api_manager import SteamAPIManager
from cartridges.utils.steamgriddb import SgdbAuthError, SgdbHelper


class SgdbManager(AsyncManager):
    """Manager in charge of downloading a game's cover from SteamGridDB"""

    run_after = (SteamAPIManager, CoverManager)
    retryable_on = (HTTPError, SSLError, ConnectionError, JSONDecodeError)

    def main(self, game: Game, _additional_data: dict) -> None:
        try:
            sgdb = SgdbHelper()
            sgdb.conditionaly_update_cover(game)
        except SgdbAuthError as error:
            # If invalid auth, cancel all SGDBManager tasks
            self.cancellable.cancel()
            raise FriendlyError(
                _("Couldn't Authenticate SteamGridDB"),
                _("Verify your API key in preferences"),
            ) from error
