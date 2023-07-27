# online_cover_manager.py
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

import logging
from pathlib import Path

import requests
from gi.repository import Gio, GdkPixbuf
from requests.exceptions import HTTPError, SSLError
from PIL import Image

from src import shared
from src.game import Game
from src.store.managers.local_cover_manager import LocalCoverManager
from src.store.managers.manager import Manager
from src.utils.save_cover import resize_cover, save_cover


class OnlineCoverManager(Manager):
    """Manager that downloads game covers from URLs"""

    run_after = (LocalCoverManager,)
    retryable_on = (HTTPError, SSLError, ConnectionError)

    def save_composited_cover(
        self,
        game: Game,
        image_file: Gio.File,
        original_width: int,
        original_height: int,
        target_width: int,
        target_height: int,
    ) -> None:
        """Save the image composited with a background blur to fit the cover size"""

        logging.debug(
            "Compositing image for %s (%s) %dx%d -> %dx%d",
            game.name,
            game.game_id,
            original_width,
            original_height,
            target_width,
            target_height,
        )

        # Load game image
        image = GdkPixbuf.Pixbuf.new_from_stream(image_file.read())

        # Create background blur of the size of the cover
        cover = image.scale_simple(2, 2, GdkPixbuf.InterpType.BILINEAR).scale_simple(
            target_width, target_height, GdkPixbuf.InterpType.BILINEAR
        )

        # Center the image above the blurred background
        scale = min(target_width / original_width, target_height / original_height)
        left_padding = (target_width - original_width * scale) / 2
        top_padding = (target_height - original_height * scale) / 2
        image.composite(
            cover,
            # Top left of overwritten area on the destination
            left_padding,
            top_padding,
            # Size of the overwritten area on the destination
            original_width * scale,
            original_height * scale,
            # Offset
            left_padding,
            top_padding,
            # Scale to apply to the resized image
            scale,
            scale,
            # Compositing stuff
            GdkPixbuf.InterpType.BILINEAR,
            255,
        )

        # Resize and save the cover
        save_cover(game.game_id, resize_cover(pixbuf=cover))

    def main(self, game: Game, additional_data: dict) -> None:
        # Ensure that we have a cover to download
        cover_url = additional_data.get("online_cover_url")
        if not cover_url:
            return

        # Download cover
        image_file = Gio.File.new_tmp()[0]
        image_path = Path(image_file.get_path())
        with requests.get(cover_url, timeout=5) as cover:
            cover.raise_for_status()
            image_path.write_bytes(cover.content)

        # Get image size
        cover_width, cover_height = shared.image_size
        with Image.open(image_path) as pil_image:
            width, height = pil_image.size

        # Composite if the image is shorter and the stretch amount is too high
        aspect_ratio = width / height
        target_aspect_ratio = cover_width / cover_height
        is_taller = aspect_ratio < target_aspect_ratio
        resized_height = height / width * cover_width
        stretch = 1 - (resized_height / cover_height)
        max_stretch = 0.12
        if is_taller or stretch <= max_stretch:
            save_cover(game.game_id, resize_cover(image_path))
        else:
            self.save_composited_cover(
                game, image_file, width, height, cover_width, cover_height
            )
