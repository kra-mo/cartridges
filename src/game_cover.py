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

from gi.repository import GdkPixbuf, Gio, GLib
from PIL import Image, ImageFilter, ImageStat


class GameCover:
    pixbuf = None
    blurred = None
    luminance = None
    path = None
    animation = None
    anim_iter = None

    placeholder_pixbuf = GdkPixbuf.Pixbuf.new_from_resource_at_scale(
        "/hu/kramo/Cartridges/library_placeholder.svg", 400, 600, False
    )

    def __init__(self, pictures, path=None):
        self.pictures = pictures
        self.new_cover(path)

    # Wrap the function in another one as Gio.Task.run_in_thread does not allow for passing args
    def create_func(self, path):
        self.animation = GdkPixbuf.PixbufAnimation.new_from_file(str(path))
        self.anim_iter = self.animation.get_iter()

        def wrapper(task, *_args):
            self.update_animation((task, self.animation))

        return wrapper

    def new_cover(self, path=None):
        self.animation = None
        self.pixbuf = None
        self.blurred = None
        self.luminance = None
        self.path = path

        if path:
            if path.suffix == ".gif":
                task = Gio.Task.new()
                task.run_in_thread(self.create_func(self.path))
            else:
                self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))

        if not self.animation:
            self.set_pixbuf(self.pixbuf)

    def get_pixbuf(self):
        return self.animation.get_static_image() if self.animation else self.pixbuf

    def get_blurred(self):
        if not self.blurred:
            if self.path:
                with Image.open(self.path) as image:
                    image = (
                        image.convert("RGB")
                        .resize((8, 12))
                        .filter(ImageFilter.GaussianBlur(3))
                    )

                    tmp_path = Gio.File.new_tmp(None)[0].get_path()
                    image.save(tmp_path, "tiff", compression=None)

                    self.blurred = GdkPixbuf.Pixbuf.new_from_file(tmp_path)

                    stat = ImageStat.Stat(image.convert("L"))

                    self.luminance = (
                        (stat.mean[0] + stat.extrema[0][0]) / 510,
                        (stat.mean[0] + stat.extrema[0][1]) / 510,
                    )
            else:
                self.blurred = GdkPixbuf.Pixbuf.new_from_resource_at_scale(
                    "/hu/kramo/Cartridges/library_placeholder.svg", 2, 3, False
                )

                self.luminance = (0.5, 0.5)

        return self.blurred

    def add_picture(self, picture):
        self.pictures.add(picture)
        if not self.animation:
            self.set_pixbuf(self.pixbuf)

    def set_pixbuf(self, pixbuf):
        self.pictures.discard(
            picture for picture in self.pictures if not picture.is_visible()
        )
        if not self.pictures:
            self.animation = None
        else:
            for picture in self.pictures:
                if not pixbuf:
                    pixbuf = self.placeholder_pixbuf
                picture.set_pixbuf(pixbuf)

    def update_animation(self, data):
        if self.animation == data[1]:
            self.anim_iter.advance()

            self.set_pixbuf(self.anim_iter.get_pixbuf())

            delay_time = self.anim_iter.get_delay_time()
            GLib.timeout_add(
                20 if delay_time < 20 else delay_time,
                self.update_animation,
                data,
            )
        else:
            data[0].return_value(False)
