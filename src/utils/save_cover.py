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

import os

from gi.repository import GdkPixbuf, Gio


def save_cover(parent_widget, game_id, cover_path, pixbuf=None):
    covers_dir = os.path.join(
        os.getenv("XDG_DATA_HOME")
        or os.path.expanduser(os.path.join("~", ".local", "share")),
        "cartridges",
        "covers",
    )

    os.makedirs(covers_dir, exist_ok=True)

    if pixbuf is None:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(cover_path, 400, 600, False)

    def cover_callback(*_unused):
        pass

    open_file = Gio.File.new_for_path(os.path.join(covers_dir, f"{game_id}.tiff"))
    parent_widget.pixbufs[game_id] = pixbuf
    pixbuf.save_to_streamv_async(
        open_file.replace(None, False, Gio.FileCreateFlags.NONE),
        "tiff",
        ["compression"],
        ["8"] if parent_widget.schema.get_boolean("high-quality-images") else ["7"],
        callback=cover_callback,
    )
