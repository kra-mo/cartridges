# game_cover.py
#
# Copyright 2022-2023 kramo
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
from typing import Optional

from gi.repository import Gdk, GdkPixbuf, Gio, GLib, Gtk
from PIL import Image, ImageFilter, ImageStat

from cartridges import shared


class GameCover:
    texture: Optional[Gdk.Texture]
    blurred: Optional[Gdk.Texture]
    luminance: Optional[tuple[float, float]]
    path: Optional[Path]
    animation: Optional[GdkPixbuf.PixbufAnimation]
    anim_iter: Optional[GdkPixbuf.PixbufAnimationIter]

    placeholder = Gdk.Texture.new_from_resource(
        shared.PREFIX + "/library_placeholder.svg"
    )
    placeholder_small = Gdk.Texture.new_from_resource(
        shared.PREFIX + "/library_placeholder_small.svg"
    )

    def __init__(self, pictures: set[Gtk.Picture], path: Optional[Path] = None) -> None:
        self.pictures = pictures
        self.new_cover(path)

    def new_cover(self, path: Optional[Path] = None) -> None:
        self.animation = None
        self.texture = None
        self.blurred = None
        self.luminance = None
        self.path = path

        if path:
            if path.suffix == ".gif":
                self.animation = GdkPixbuf.PixbufAnimation.new_from_file(str(path))
                self.anim_iter = self.animation.get_iter()
                self.task = Gio.Task.new()
                self.task.run_in_thread(
                    lambda *_: self.update_animation((self.task, self.animation))
                )
            else:
                self.texture = Gdk.Texture.new_from_filename(str(path))

        if not self.animation:
            self.set_texture(self.texture)

    def get_texture(self) -> Gdk.Texture:
        return (
            Gdk.Texture.new_for_pixbuf(self.animation.get_static_image())
            if self.animation
            else self.texture
        )

    def get_blurred(self) -> Gdk.Texture:
        if not self.blurred:
            if self.path:
                with Image.open(self.path) as image:
                    image = (
                        image.convert("RGB")
                        .resize((100, 150))
                        .filter(ImageFilter.GaussianBlur(20))
                    )

                    tmp_path = Gio.File.new_tmp(None)[0].get_path()
                    image.save(tmp_path, "tiff", compression=None)

                    self.blurred = Gdk.Texture.new_from_filename(tmp_path)

                    stat = ImageStat.Stat(image.convert("L"))

                    # Luminance values for light and dark mode
                    self.luminance = (
                        min((stat.mean[0] + stat.extrema[0][0]) / 510, 0.7),
                        max((stat.mean[0] + stat.extrema[0][1]) / 510, 0.3),
                    )
            else:
                self.blurred = self.placeholder_small
                self.luminance = (0.3, 0.5)

        return self.blurred

    def add_picture(self, picture: Gtk.Picture) -> None:
        self.pictures.add(picture)
        if not self.animation:
            self.set_texture(self.texture)
        else:
            self.update_animation((self.task, self.animation))

    def set_texture(self, texture: Gdk.Texture) -> None:
        self.pictures.discard(
            picture for picture in self.pictures if not picture.is_visible()
        )
        if not self.pictures:
            self.animation = None
        else:
            for picture in self.pictures:
                picture.set_paintable(texture or self.placeholder)

    def update_animation(self, data: GdkPixbuf.PixbufAnimation) -> None:
        if self.animation == data[1]:
            self.anim_iter.advance()  # type: ignore

            self.set_texture(Gdk.Texture.new_for_pixbuf(self.anim_iter.get_pixbuf()))  # type: ignore

            delay_time = self.anim_iter.get_delay_time()  # type: ignore
            GLib.timeout_add(
                20 if delay_time < 20 else delay_time,
                self.update_animation,
                data,
            )
