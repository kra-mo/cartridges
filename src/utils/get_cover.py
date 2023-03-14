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

def get_cover(game_id, parent_widget):
    from gi.repository import GdkPixbuf
    import os

    if game_id in parent_widget.pixbufs.keys():
        return parent_widget.pixbufs[game_id]
    cover_path = os.path.join(os.environ.get("XDG_DATA_HOME"), "cartridges", "covers", game_id + ".png")

    if os.path.isfile(cover_path) == False:
        return parent_widget.placeholder_pixbuf

    return GdkPixbuf.Pixbuf.new_from_file(cover_path)
