# local_cover_manager.py
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
