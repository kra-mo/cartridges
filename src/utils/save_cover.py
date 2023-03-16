# save_cover.py
#
# Copyright 2022 kramo
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


def save_cover(game, parent_widget, file_path, pixbuf=None, game_id=None):
    covers_dir = os.path.join(
        os.getenv("XDG_DATA_HOME")
        or os.path.expanduser(os.path.join("~", ".local", "share")),
        "cartridges",
        "covers",
    )
    if not os.path.exists(covers_dir):
        os.makedirs(covers_dir)

    if game_id is None:
        game_id = game["game_id"]

    if pixbuf is None:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(file_path, 600, 900, False)

    def cover_callback(*_unused):
        pass

    open_file = Gio.File.new_for_path(os.path.join(covers_dir, game_id + ".tiff"))
    parent_widget.pixbufs[game_id] = pixbuf
    pixbuf.save_to_streamv_async(
        open_file.replace(None, False, Gio.FileCreateFlags.NONE),
        "tiff",
        ["compression"],
        ["7"],
        callback=cover_callback,
    )
