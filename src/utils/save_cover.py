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

from gi.repository import GdkPixbuf, Gio
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
    win,
    game_id,
    cover_path=None,
    pixbuf=None,
    animation_path=None,
):
    win.covers_dir.mkdir(parents=True, exist_ok=True)

    # Remove previous covers
    (win.covers_dir / f"{game_id}.tiff").unlink(missing_ok=True)
    (win.covers_dir / f"{game_id}.gif").unlink(missing_ok=True)

    if animation_path:
        copyfile(animation_path, win.covers_dir / f"{game_id}.gif")
        win.game_covers[game_id].new_pixbuf(animation_path)
        return

    if not pixbuf:
        if not cover_path:
            return
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            str(cover_path), *win.image_size, False
        )

    pixbuf.savev(
        str(win.covers_dir / f"{game_id}.tiff"),
        "tiff",
        ["compression"],
        ["8"] if win.schema.get_boolean("high-quality-images") else ["7"],
    )

    if game_id in win.game_covers:
        win.game_covers[game_id].new_pixbuf(win.covers_dir / f"{game_id}.tiff")
