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

from .get_cover import get_cover


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/game.ui")
class game(Gtk.Box):
    __gtype_name__ = "game"

    overlay = Gtk.Template.Child()
    title = Gtk.Template.Child()
    button_play = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()
    play_revealer = Gtk.Template.Child()
    title_revealer = Gtk.Template.Child()

    def __init__(self, parent_widget, data, **kwargs):
        super().__init__(**kwargs)

        self.parent_widget = parent_widget
        self.added = data["added"]
        self.executable = data["executable"]
        self.game_id = data["game_id"]
        self.hidden = data["hidden"]
        self.last_played = data["last_played"]
        self.name = data["name"]

        if "removed" in data.keys():
            self.removed = True
        else:
            self.removed = False

        self.pixbuf = get_cover(self.game_id, self.parent_widget)

        self.cover.set_pixbuf(self.pixbuf)
        self.title.set_label(self.name)

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_contoller_motion)
        self.overlay.set_measure_overlay(self.play_revealer, True)

        self.button_play.connect("clicked", self.launch_game)
        self.event_contoller_motion.connect("enter", self.show_play)
        self.event_contoller_motion.connect("leave", self.hide_play)
        self.menu_button.get_popover().connect("notify::visible", self.hide_play)

    def show_play(self, _widget, *args):
        self.play_revealer.set_reveal_child(True)
        self.title_revealer.set_reveal_child(False)

    def hide_play(self, _widget, *args):
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(False)
            self.title_revealer.set_reveal_child(True)

    def launch_game(self, _widget):
        self.parent_widget.set_active_game(None, None, self.game_id)
        self.parent_widget.get_application().on_launch_game_action(None)
