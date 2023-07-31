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

from pathlib import Path
from typing import NamedTuple, Sequence

import cairo
from cairo import ImageSurface, Context, SurfacePattern
import requests
from gi.repository import Gio, GdkPixbuf
from PIL import Image
from requests.exceptions import HTTPError, SSLError

from src import shared
from src.game import Game
from src.store.managers.manager import Manager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.utils.save_cover import resize_cover, save_cover


class UnsupportedGdkPixbufBitDepth(Exception):
    """Error raised when a GdkPixbuf has an unsupported bit depth"""


class UnsupportedGdkPixbufChannels(Exception):
    """Error raised when a GdkPixbuf has an unexpected number of channels"""


def swap_buffer_channels(buffer: bytearray, swap_destinations: Sequence[int]) -> None:
    """
    Swap in place the color channels in a bytearray.

    For example, aRGB to RGBa
    `self.swap_bytearray_channels(buffer, (3,0,1,2))

    :param swaps: (source, target) swaps to perform
    """
    n_channels = len(swap_destinations)
    n_pixels = int(len(buffer) / n_channels)
    for pixel_index in range(n_pixels):
        pixel_data_copy = bytearray(buffer[pixel_index : pixel_index + n_channels + 1])
        for source_channel, destination_channel in enumerate(swap_destinations):
            buffer[pixel_index + destination_channel] = pixel_data_copy[source_channel]


def rotate_buffer_channels(
    buffer: bytearray, n_channels: int = 4, shift: int = 1
) -> None:
    """
    Rotate in place the color channels in a bytearray

    :param buffer: buffer to edit in place
    :param n_channels: number of 1 byte color channels
    :param shift: number of places to shift. Use negative values to shift left.
    """
    swap_destinations = []
    for source_channel in range(n_channels):
        destination_channel = (source_channel + shift) % n_channels
        swap_destinations.append(destination_channel)
    swap_buffer_channels(buffer, swap_destinations)


class ImageSize(NamedTuple):
    width: float = 0
    height: float = 0

    @property
    def aspect_ratio(self) -> float:
        return self.width / self.height

    def __str__(self):
        return f"{self.width}x{self.height}"

    def __mul__(self, scale: float | int) -> "ImageSize":
        return ImageSize(
            self.width * scale,
            self.height * scale,
        )

    def __truediv__(self, divisor: float | int) -> "ImageSize":
        return self * (1 / divisor)

    def __add__(self, other_size: "ImageSize") -> "ImageSize":
        return ImageSize(
            self.width + other_size.width,
            self.height + other_size.height,
        )

    def __sub__(self, other_size: "ImageSize") -> "ImageSize":
        return self + (other_size * -1)


class ImageSurfaceBuilder:
    """Utility class to build cairo ImageSurface-s"""

    @property
    def _supported_pixbuf_extensions(self) -> set[str]:
        """
        Get the list of image file extension supported by gdkpixbuf

        Extensions are returned with a leading ".", even though
        GdkPixbuf.PixbufFormat.extensions don't have it.
        """
        extensions = set()
        for gdkpixbuf_format in GdkPixbuf.Pixbuf.get_formats():
            for extension in gdkpixbuf_format.extensions:
                extensions.add(f".{extension}")
        return extensions

    def _from_path_using_gdkpixbuf(self, path: Path) -> ImageSurface:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
        buffer: bytes | bytearray
        cairo_format: cairo.Format

        # With alpha
        if pixbuf.get_has_alpha():
            # Pixbufs: RGBa | cairo's closest format: aRGB
            # https://docs.gtk.org/gdk-pixbuf/class.Pixbuf.html#image-data
            # https://www.cairographics.org/manual/cairo-Image-Surfaces.html#cairo-format-t
            buffer = bytearray(pixbuf.get_pixels())
            rotate_buffer_channels(buffer, 4, 1)
            cairo_format = cairo.Format.ARGB32

        # Without alpha
        else:
            buffer = pixbuf.get_pixels()
            cairo_format = cairo.Format.RGB24

        return ImageSurface.create_for_data(
            buffer,
            cairo_format,
            pixbuf.get_width(),
            pixbuf.get_height(),
            pixbuf.get_rowstride(),
        )

    def _from_path_using_pil(self, path: Path):
        with Image.open(path) as image:
            if image.format != "RGBA":
                if image.format == "RGB":
                    image.putalpha(256)
                else:
                    image = image.convert(mode="RGBA")
            buffer = bytearray(image.tobytes("raw", "RGBA"))
            rotate_buffer_channels(buffer, 4, 1)
            return cairo.ImageSurface.create_for_data(
                buffer, cairo.Format.ARGB32, image.width, image.height
            )

    def from_path(self, path: Path) -> ImageSurface:
        """
        Get a cairo surface from an image path
        using the most optimal method for the given file format
        """
        extension = path.suffix
        if extension == ".png":
            return ImageSurface.create_from_png(path)
        if extension in self._supported_pixbuf_extensions:
            return self._from_path_using_gdkpixbuf(path)
        return self._from_path_using_pil(path)


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

    def save_composited_cover(
        self,
        game: Game,
        image_path: Path,
        scale: float = 1,
        blur_size: ImageSize = ImageSize(2, 2),
    ) -> None:
        """
        Save the image composited with a background blur.

        1. Downscale the image to the blur size
        2. Fill the cover by stretching the downscaled image
        3. Scale the original image to be as big as possible with no overflow
        4. Scale it to the (optional) specified factor
        5. Center the image on the cover, above the blur
        6. Save the cover

        :param game: The game to save the cover for
        :param path: Path where the source image is located
        :param scale:
            Scale of the smalled image side
            compared to the corresponding side in the cover
        :param blur_size: Size of the downscaled image used for the blur
        """

        # Create the cover surface
        cover_size = ImageSize._make(shared.image_size)
        cover = ImageSurface(cairo.Format.ARGB32, *cover_size)
        cover_ctx = Context(cover)

        # Load source image
        source_surface = ImageSurfaceBuilder().from_path(image_path)
        source_size = ImageSize(source_surface.get_width(), source_surface.get_height())
        source_pattern = SurfacePattern(source_surface)
        source_pattern.set_filter(cairo.Filter.BILINEAR)

        # Create a small color grid from the source image
        blur = ImageSurface(cairo.Format.ARGB32, *blur_size)
        Context(blur).set_source(source_pattern).rectangle(0, 0, *blur_size).fill()

        # Stretch the color grid to create a blurred cover background
        blur_pattern = SurfacePattern(blur)
        blur_pattern.set_filter(cairo.Filter.BILINEAR)
        cover_ctx.rectangle(0, 0, *cover_size)
        cover_ctx.set_source(blur_pattern)
        cover_ctx.fill()

        # Compute image scale
        fit_scale = min(
            cover_dimension / source_dimension
            for cover_dimension, source_dimension in zip(cover_size, source_size)
        )
        scaled_size = source_size * fit_scale * scale
        padding = cover_size - scaled_size / 2

        # Apply scale and center in the cover
        cover_ctx.rectangle(*padding, *scaled_size)
        cover_ctx.set_source(source_pattern)
        cover_ctx.fill()

        # Save cover
        cover_path = Path(Gio.File.new_tmp("XXXXXX.png")[0].get_path())
        cover.write_to_png(cover_path)
        save_cover(game.game_id, resize_cover(cover_path))

    def main(self, game: Game, additional_data: dict) -> None:
        for key in (
            "local_image_path",
            "local_icon_path",
            "online_cover_url",
        ):
            # Get an image path
            if not (value := additional_data.get(key)):
                continue
            if key == "online_cover_url":
                image_path = self.download_image(value)
            else:
                image_path = Path(value)
            if not image_path.is_file():
                continue

            # Icon cover
            if key == "local_icon_path":
                self.save_composited_cover(
                    game, image_path, scale=0.7, blur_size=ImageSize(1, 2)
                )
                return

            # Stretchable cover with no compositing
            source_size = self.get_image_size(image_path)
            cover_size = ImageSize._make(shared.image_size)
            if self.is_stretchable(source_size, cover_size):
                save_cover(game.game_id, resize_cover(image_path))
                return

            # Other covers, composite with a background blur
            self.save_composited_cover(game, image_path)
