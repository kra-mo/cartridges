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

import logging
from pathlib import Path
from typing import NamedTuple

import requests
from gi.repository import GdkPixbuf, Gio
from PIL import Image
from requests.exceptions import HTTPError, SSLError

from src import shared
from src.game import Game
from src.store.managers.manager import Manager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.utils.save_cover import resize_cover, save_cover


class ImageSize(NamedTuple):
    width: float
    height: float

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def __str__(self):
        return f"{self.width}x{self.height}"

    def __mul__(self, scale: float) -> "ImageSize":
        return ImageSize(self.width * scale, self.height * scale)


class CoverManager(Manager):
    """
    Manager in charge of adding the cover image of the game

    Order of priority is:
    1. local cover
    2. icon cover
    3. online cover
    """

    run_after = (SteamAPIManager,)
    retryable_on = (HTTPError, SSLError, ConnectionError)

    def save_composited_cover(
        self, game: Game, path: Path, source_size: ImageSize, target_size: ImageSize
    ) -> None:
        """
        Save the image composited with a background blur

        Will scale the source image size as much as possible
        while not overflowing the target size.
        """

        logging.debug(
            "Compositing image for %s (%s) %s -> %s",
            game.name,
            game.game_id,
            str(source_size),
            str(target_size),
        )

        # Load game image
        image = GdkPixbuf.Pixbuf.new_from_file(str(path))

        # Create background blur of the size of the cover
        cover = image.scale_simple(2, 2, GdkPixbuf.InterpType.BILINEAR).scale_simple(
            target_size.width, target_size.height, GdkPixbuf.InterpType.BILINEAR
        )

        # Center the image above the blurred background
        scale = min(
            target_size.width / source_size.width,
            target_size.height / source_size.height,
        )
        left_padding = (target_size.width - source_size.width * scale) / 2
        top_padding = (target_size.height - source_size.height * scale) / 2
        image.composite(
            cover,
            # Top left of overwritten area on the destination
            left_padding,
            top_padding,
            # Size of the overwritten area on the destination
            source_size.width * scale,
            source_size.height * scale,
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

    def download_image(self, url: str) -> Path:
        image_file = Gio.File.new_tmp()[0]
        path = Path(image_file.get_path())
        with requests.get(url, timeout=5) as cover:
            cover.raise_for_status()
            path.write_bytes(cover.content)
        return path

    def get_image_size(self, path: Path) -> ImageSize:
        with Image.open(path) as image:
            return ImageSize._make(image.size)

    def is_stretchable(self, source_size: ImageSize, cover_size: ImageSize) -> bool:
        is_taller = source_size.aspect_ratio < cover_size.aspect_ratio
        if is_taller:
            return True
        max_stretch = 0.12
        resized_height = (1 / source_size.aspect_ratio) * cover_size.width
        stretch = 1 - (resized_height / cover_size.height)
        return stretch <= max_stretch

    def main(self, game: Game, additional_data: dict) -> None:
        for key in ("local_image_path", "local_icon_path", "online_cover_url"):
            # Get an image path
            if not (value := additional_data.get(key)):
                continue
            if key == "online_cover_url":
                path = self.download_image(value)
            else:
                path = Path(value)
            if not path.is_file():
                continue

            # Save the cover with the necessary compositing
            cover_size = ImageSize._make(shared.image_size)
            if key == "local_icon_path":
                target_size = cover_size * 0.7
                self.save_composited_cover(game, path, target_size, target_size)
                return
            source_size = self.get_image_size(path)
            if self.is_stretchable(source_size, cover_size):
                save_cover(game.game_id, resize_cover(path))
                return
            self.save_composited_cover(game, path, source_size, cover_size)
