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

    overlay = Gtk.Template.Child()
    title = Gtk.Template.Child()
    button_play = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()
    button_revealer = Gtk.Template.Child()
    title_revealer = Gtk.Template.Child()
    menu_revealer = Gtk.Template.Child()

    def __init__(self, parent_widget, title, pixbuf, game_id, **kwargs):
        super().__init__(**kwargs)

        self.parent_widget = parent_widget
        self.name = title
        self.pixbuf = pixbuf
        self.game_id = game_id

        self.title.set_label(title)
        self.cover.set_pixbuf(pixbuf)

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.overlay.add_controller(self.event_contoller_motion)
        self.overlay.set_measure_overlay(self.button_revealer, True)
        self.overlay.set_measure_overlay(self.menu_revealer, True)

        self.button_play.connect("clicked", self.launch_game)
        self.event_contoller_motion.connect("enter", self.show_play)
        self.event_contoller_motion.connect("leave", self.hide_play)
        self.menu_button.get_popover().connect("notify::visible", self.hide_play)

    def show_play(self, widget, *args):
        self.button_revealer.set_reveal_child(True)
        self.title_revealer.set_reveal_child(False)
        self.menu_revealer.set_reveal_child(True)

    def hide_play(self, widget, *args):
        if not self.menu_button.get_active():
            self.button_revealer.set_reveal_child(False)
            self.title_revealer.set_reveal_child(True)
            self.menu_revealer.set_reveal_child(False)

    def launch_game(self, widget):
        self.parent_widget.set_active_game(None, None, self.game_id)
        self.parent_widget.get_application().on_launch_game_action(None)
