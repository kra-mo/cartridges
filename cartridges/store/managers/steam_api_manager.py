# steam_api_manager.py
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

from requests.exceptions import HTTPError, SSLError
from urllib3.exceptions import ConnectionError as Urllib3ConnectionError

from cartridges.game import Game
from cartridges.store.managers.async_manager import AsyncManager
from cartridges.utils.steam import (
    SteamAPIHelper,
    SteamGameNotFoundError,
    SteamNotAGameError,
    SteamRateLimiter,
)


class SteamAPIManager(AsyncManager):
    """Manager in charge of completing a game's data from the Steam API"""

    retryable_on = (HTTPError, SSLError, Urllib3ConnectionError)

    steam_api_helper: SteamAPIHelper = None
    steam_rate_limiter: SteamRateLimiter = None

    def __init__(self) -> None:
        super().__init__()
        self.steam_rate_limiter = SteamRateLimiter()
        self.steam_api_helper = SteamAPIHelper(self.steam_rate_limiter)

    def main(self, game: Game, additional_data: dict) -> None:
        # Skip non-Steam games
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
