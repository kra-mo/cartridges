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

def save_cover(game, parent_widget, file_path, pixbuf = None, game_id = None):
    from gi.repository import Gio, GdkPixbuf
    import os

    covers_dir = os.path.join(os.environ.get("XDG_DATA_HOME"), "cartridges", "covers")
    if os.path.exists(covers_dir) == False:
        os.makedirs(covers_dir)

    if game_id == None:
        game_id = game["game_id"]

    cover_path = os.path.join(covers_dir, game_id + ".dat")

    if pixbuf == None:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(file_path, 600, 900, False)

    def cover_callback(*args):
        pass

    file = Gio.File.new_for_path(os.path.join(covers_dir, game_id + ".png"))
    parent_widget.pixbufs[game_id] = pixbuf
    pixbuf.save_to_streamv_async(file.replace(None, False, Gio.FileCreateFlags.NONE), "png", None, None, None, cover_callback)
