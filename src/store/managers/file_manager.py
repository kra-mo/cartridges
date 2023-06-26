# file_manager.py
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

import json

from src import shared
from src.game import Game
from src.store.managers.async_manager import AsyncManager
from src.store.managers.steam_api_manager import SteamAPIManager


class FileManager(AsyncManager):
    """Manager in charge of saving a game to a file"""

    run_after = (SteamAPIManager,)
    signals = {"save-ready"}

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        if additional_data.get("skip_save"):  # Skip saving when loading games from disk
            return

        shared.games_dir.mkdir(parents=True, exist_ok=True)

        attrs = (
            "added",
            "executable",
            "game_id",
            "source",
            "hidden",
            "last_played",
            "name",
            "developer",
            "removed",
            "blacklisted",
            "version",
        )

        json.dump(
            {attr: getattr(game, attr) for attr in attrs if attr},
            (shared.games_dir / f"{game.game_id}.json").open("w"),
            indent=4,
            sort_keys=True,
        )
