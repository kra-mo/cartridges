# save_cover.py
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
from shutil import copyfile

from gi.repository import GdkPixbuf, Gio, GLib
from PIL import Image, ImageSequence


def resize_animation(cover_path):
    image = Image.open(cover_path)
    frames = tuple(
        frame.copy().resize((200, 300)) for frame in ImageSequence.Iterator(image)
    )

    tmp_path = Path(Gio.File.new_tmp("XXXXXX.gif")[0].get_path())
    frames[0].save(
        tmp_path,
        format="gif",
        save_all=True,
        append_images=frames[1:],
    )

    return tmp_path


def save_cover(
    parent_widget, game_id, cover_path=None, pixbuf=None, animation_path=None
):
    covers_dir = parent_widget.data_dir / "cartridges" / "covers"

    covers_dir.mkdir(parents=True, exist_ok=True)

    if animation_path:
        pixbuf = GdkPixbuf.PixbufAnimation.new_from_file(
            str(animation_path)
        ).get_static_image()
    elif not pixbuf:
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(cover_path), *parent_widget.image_size, False
            )
        except GLib.GError:
            return

    open_file = Gio.File.new_for_path(str(covers_dir / f"{game_id}.tiff"))
    pixbuf.save_to_streamv(
        open_file.replace(None, False, Gio.FileCreateFlags.NONE),
        "tiff",
        ["compression"],
        ["8"] if parent_widget.schema.get_boolean("high-quality-images") else ["7"],
    )

    if animation_path:
        animation_dir = parent_widget.data_dir / "cartridges" / "animated_covers"
        animation_dir.mkdir(parents=True, exist_ok=True)

        copyfile(animation_path, animation_dir / f"{game_id}.gif")
