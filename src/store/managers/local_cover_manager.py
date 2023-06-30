# local_cover_manager.py
#
# Copyright 2023 Geoffrey Coulaud
# Copyright 2023 kramo
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

from gi.repository import GdkPixbuf

from src import shared
from src.game import Game
from src.store.managers.manager import Manager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.utils.save_cover import resize_cover, save_cover


class LocalCoverManager(Manager):
    """Manager in charge of adding the local cover image of the game"""

    run_after = (SteamAPIManager,)

    def manager_logic(self, game: Game, additional_data: dict) -> None:
        if image_path := additional_data.get("local_image_path"):
            if not image_path.is_file():
                return
            save_cover(game.game_id, resize_cover(image_path))
        elif icon_path := additional_data.get("local_icon_path"):
            cover_width, cover_height = shared.image_size

            dest_width = cover_width * 0.7
            dest_height = cover_width * 0.7

            dest_x = cover_width * 0.15
            dest_y = (cover_height - dest_height) / 2

            image = GdkPixbuf.Pixbuf.new_from_file(str(icon_path)).scale_simple(
                dest_width, dest_height, GdkPixbuf.InterpType.BILINEAR
            )

            cover = image.scale_simple(
                1, 2, GdkPixbuf.InterpType.BILINEAR
            ).scale_simple(cover_width, cover_height, GdkPixbuf.InterpType.BILINEAR)

            image.composite(
                cover,
                dest_x,
                dest_y,
                dest_width,
                dest_height,
                dest_x,
                dest_y,
                1,
                1,
                GdkPixbuf.InterpType.BILINEAR,
                255,
            )

            save_cover(game.game_id, resize_cover(pixbuf=cover))
