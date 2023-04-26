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

from gi.repository import Gio
from PIL import Image, ImageSequence


def resize_cover(win, cover_path=None, pixbuf=None):
    if not cover_path and not pixbuf:
        return None

    if pixbuf:
        cover_path = Path(Gio.File.new_tmp("XXXXXX.tiff")[0].get_path())
        pixbuf.savev(str(cover_path), "tiff", ["compression"], ["1"])

    with Image.open(cover_path) as image:
        if getattr(image, "is_animated", False):
            frames = tuple(
                frame.copy().resize((200, 300))
                for frame in ImageSequence.Iterator(image)
            )

            tmp_path = Path(Gio.File.new_tmp("XXXXXX.gif")[0].get_path())
            frames[0].save(
                tmp_path,
                save_all=True,
                append_images=frames[1:],
            )

        else:
            # This might not be necessary in the future
            # https://github.com/python-pillow/Pillow/issues/2663
            if image.mode not in ("RGB", "RGBA"):
                image = image.convert("RGBA")

            tmp_path = Path(Gio.File.new_tmp("XXXXXX.tiff")[0].get_path())
            image.resize(win.image_size).save(
                tmp_path,
                compression="tiff_adobe_deflate"
                if win.schema.get_boolean("high-quality-images")
                else "webp",
            )

    return tmp_path


def save_cover(win, game_id, cover_path):
    win.covers_dir.mkdir(parents=True, exist_ok=True)

    animated_path = win.covers_dir / f"{game_id}.gif"
    static_path = win.covers_dir / f"{game_id}.tiff"

    # Remove previous covers
    animated_path.unlink(missing_ok=True)
    static_path.unlink(missing_ok=True)

    if not cover_path:
        return

    copyfile(
        cover_path,
        animated_path if cover_path.suffix == ".gif" else static_path,
    )

    if game_id in win.game_covers:
        win.game_covers[game_id].new_cover(
            animated_path if cover_path.suffix == ".gif" else static_path
        )
