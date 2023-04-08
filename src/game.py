# game.py
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

import json
import os
import shlex  # pylint: disable=unused-import
import subprocess
import sys

from gi.repository import GdkPixbuf, Gio, Gtk

from .save_game import save_game


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/game.ui")
class game(Gtk.Box):  # pylint: disable=invalid-name
    __gtype_name__ = "game"

    overlay = Gtk.Template.Child()
    title = Gtk.Template.Child()
    button_play = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    play_revealer = Gtk.Template.Child()
    title_revealer = Gtk.Template.Child()
    game_options = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()

    def __init__(self, parent_widget, data, **kwargs):
        super().__init__(**kwargs)

        self.parent_widget = parent_widget
        self.added = data["added"]
        self.executable = data["executable"]
        self.game_id = data["game_id"]
        self.hidden = data["hidden"]
        self.last_played = data["last_played"]
        self.name = data["name"]
        self.developer = data["developer"] if "developer" in data else None
        self.removed = "removed" in data
        self.blacklisted = "blacklisted" in data

        self.pixbuf = self.get_cover()

        self.cover.set_pixbuf(self.pixbuf)
        self.title.set_label(self.name)

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_contoller_motion)
        self.overlay.set_measure_overlay(self.play_revealer, True)

        self.set_play_label()

        self.cover_button.connect("clicked", self.cover_button_clicked)
        self.button_play.connect("clicked", self.button_play_clicked)

        self.event_contoller_motion.connect("enter", self.show_play)
        self.event_contoller_motion.connect("leave", self.hide_play)

        self.parent_widget.schema.connect("changed", self.schema_changed)

        if self.hidden:
            self.menu_button.set_menu_model(self.hidden_game_options)
        else:
            self.menu_button.set_menu_model(self.game_options)
        self.menu_button.get_popover().connect("notify::visible", self.hide_play)

    def launch(self):
        # Generate launch arguments, either list (no shell) or a string (for shell).
        args = (
            ["flatpak-spawn", "--host", *self.executable]  # Flatpak
            if os.getenv("FLATPAK_ID") == "hu.kramo.Cartridges"
            else shlex.join(
                self.executable
            )  # Windows (We need shell to support its "open" built-in).
            if os.name == "nt"
            else self.executable  # Linux/Others
        )

        # The host environment vars are automatically passed through by Popen.
        subprocess.Popen(
            args,
            shell=isinstance(args, str),
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
        if Gio.Settings.new("hu.kramo.Cartridges").get_boolean("exit-after-launch"):
            sys.exit()

    def toggle_hidden(self):
        games_dir = self.parent_widget.data_dir / "cartridges" / "games"

        if not games_dir.exists():
            return

        data = json.loads((games_dir / f"{self.game_id}.json").read_text("utf-8"))

        data["hidden"] = not data["hidden"]

        save_game(self.parent_widget, data)

    def get_cover(self):
        # If the cover is already in memory, return
        if self.game_id in self.parent_widget.pixbufs:
            return self.parent_widget.pixbufs[self.game_id]

        # Create a new pixbuf
        cover_path = (
            self.parent_widget.data_dir
            / "cartridges"
            / "covers"
            / f"{self.game_id}.tiff"
        )

        if cover_path.is_file():
            return GdkPixbuf.Pixbuf.new_from_file(str(cover_path))

        # Return the placeholder pixbuf
        return self.parent_widget.placeholder_pixbuf

    def show_play(self, _widget, *_unused):
        self.play_revealer.set_reveal_child(True)
        self.title_revealer.set_reveal_child(False)

    def hide_play(self, _widget, *_unused):
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(False)
            self.title_revealer.set_reveal_child(True)

    def launch_game(self, _widget, *_unused):
        self.parent_widget.set_active_game(None, None, self.game_id)
        self.parent_widget.get_application().on_launch_game_action(None)

    def cover_button_clicked(self, _widget):
        if self.parent_widget.schema.get_boolean("cover-launches-game"):
            self.launch_game(None)
        else:
            self.parent_widget.show_overview(None, self.game_id)

    def button_play_clicked(self, _widget):
        if self.parent_widget.schema.get_boolean("cover-launches-game"):
            self.parent_widget.show_overview(None, self.game_id)
        else:
            self.launch_game(None)

    def set_play_label(self):
        if self.parent_widget.schema.get_boolean("cover-launches-game"):
            self.button_play.set_label(_("Details"))
        else:
            self.button_play.set_label(_("Play"))

    def schema_changed(self, _settings, key):
        if key == "cover-launches-game":
            self.set_play_label()
