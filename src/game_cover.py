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

from gi.repository import GdkPixbuf


class GameCover:
    placeholder_pixbuf = GdkPixbuf.Pixbuf.new_from_resource_at_scale(
        "/hu/kramo/Cartridges/library_placeholder.svg", 400, 600, False
    )

    def __init__(self, picture, pixbuf=None, path=None):
        self.picture = picture
        self.pixbuf = pixbuf

        if path:
            self.pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)

        if not self.pixbuf:
            self.pixbuf = self.placeholder_pixbuf

        self.update_pixbuf()

    def get_pixbuf(self):
        return self.pixbuf

    def update_pixbuf(self):
        self.picture.set_pixbuf(self.pixbuf)
