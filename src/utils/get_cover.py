# get_cover.py
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

def get_cover(game, parent_widget):
    from gi.repository import GdkPixbuf
    import os

    cover_path = os.path.join(os.environ.get("XDG_DATA_HOME"), "cartridges", "covers", game["game_id"] + ".dat")

    if os.path.isfile(cover_path) == False:
        return parent_widget.placeholder_pixbuf

    open_file = open((cover_path), "rb")
    data = open_file.read()
    open_file.close()
    try:
        return GdkPixbuf.Pixbuf.new_from_data(data, *parent_widget.games[game["game_id"]]["pixbuf_options"])
    except KeyError:
        return parent_widget.placeholder_pixbuf
