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
from typing import Optional

from gi.repository import Gdk, GdkPixbuf, Gio, GLib
from PIL import Image, ImageSequence, UnidentifiedImageError

from cartridges import shared


def convert_cover(
    cover_path: Optional[Path] = None,
    pixbuf: Optional[GdkPixbuf.Pixbuf] = None,
    resize: bool = True,
) -> Optional[Path]:
    if not cover_path and not pixbuf:
        return None

    pixbuf_extensions = set()
    for pixbuf_format in GdkPixbuf.Pixbuf.get_formats():
        for pixbuf_extension in pixbuf_format.get_extensions():
            pixbuf_extensions.add(pixbuf_extension)

    if not resize and cover_path and cover_path.suffix.lower()[1:] in pixbuf_extensions:
        return cover_path

    if pixbuf:
        cover_path = Path(Gio.File.new_tmp("XXXXXX.tiff")[0].get_path())
        pixbuf.savev(str(cover_path), "tiff", ["compression"], ["1"])

    try:
        with Image.open(cover_path) as image:
            if getattr(image, "is_animated", False):
                frames = tuple(
                    frame.resize((200, 300)) if resize else frame
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
                (image.resize(shared.image_size) if resize else image).save(
                    tmp_path,
                    compression="tiff_adobe_deflate"
                    if shared.schema.get_boolean("high-quality-images")
                    else shared.TIFF_COMPRESSION,
                )
    except UnidentifiedImageError:
        try:
            Gdk.Texture.new_from_filename(str(cover_path)).save_to_tiff(
                tmp_path := Gio.File.new_tmp("XXXXXX.tiff")[0].get_path()
            )
            return convert_cover(tmp_path)
        except GLib.Error:
            return None

    return tmp_path


def save_cover(game_id: str, cover_path: Path) -> None:
    shared.covers_dir.mkdir(parents=True, exist_ok=True)

    animated_path = shared.covers_dir / f"{game_id}.gif"
    static_path = shared.covers_dir / f"{game_id}.tiff"

    # Remove previous covers
    animated_path.unlink(missing_ok=True)
    static_path.unlink(missing_ok=True)

    if not cover_path:
        return

    copyfile(
        cover_path,
        animated_path if cover_path.suffix == ".gif" else static_path,
    )

    if game_id in shared.win.game_covers:
        shared.win.game_covers[game_id].new_cover(
            animated_path if cover_path.suffix == ".gif" else static_path
        )
