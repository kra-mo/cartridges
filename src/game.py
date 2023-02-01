# game.py
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

from gi.repository import Gtk

@Gtk.Template(resource_path='/hu/kramo/Cartridges/gtk/game.ui')
class game(Gtk.Box):
    __gtype_name__ = 'game'

    title = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()

    def __init__(self, title, pixbuf, game_id, **kwargs):
        super().__init__(**kwargs)

        self.name = title
        self.pixbuf = pixbuf
        self.game_id = game_id

        self.title.set_label(title)
        self.cover.set_pixbuf(pixbuf)
