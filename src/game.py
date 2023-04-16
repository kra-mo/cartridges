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

from gi.repository import Gio, Gtk

from .game_cover import GameCover
from .save_game import save_game


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/game.ui")
class Game(Gtk.Box):
    __gtype_name__ = "Game"

    overlay = Gtk.Template.Child()
    title = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    play_revealer = Gtk.Template.Child()
    title_revealer = Gtk.Template.Child()
    game_options = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()

    def __init__(self, win, data, **kwargs):
        super().__init__(**kwargs)

        self.win = win
        self.added = data["added"]
        self.executable = data["executable"]
        self.game_id = data["game_id"]
        self.hidden = data["hidden"]
        self.last_played = data["last_played"]
        self.name = data["name"]
        self.developer = data["developer"] if "developer" in data else None
        self.removed = "removed" in data
        self.blacklisted = "blacklisted" in data

        self.loading = 0
        self.title.set_label(self.name)

        if self.game_id in self.win.game_covers:
            self.win.game_covers[self.game_id].add_picture(self.cover)
        else:
            game_cover = GameCover({self.cover}, self.get_cover_path())
            self.win.game_covers[self.game_id] = game_cover

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_contoller_motion)
        self.overlay.set_measure_overlay(self.play_revealer, True)

        self.set_play_label()

        self.cover_button.connect("clicked", self.cover_button_clicked)
        self.play_button.connect("clicked", self.play_button_clicked)

        self.event_contoller_motion.connect("enter", self.show_play)
        self.event_contoller_motion.connect("leave", self.hide_play)

        self.win.schema.connect("changed", self.schema_changed)

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
        data = json.loads(
            (self.win.games_dir / f"{self.game_id}.json").read_text("utf-8")
        )

        data["hidden"] = not data["hidden"]

        save_game(self.win, data)

    def get_cover_path(self):
        cover_path = self.win.covers_dir / f"{self.game_id}.gif"
        if cover_path.is_file():
            return cover_path

        cover_path = self.win.covers_dir / f"{self.game_id}.tiff"
        if cover_path.is_file():
            return cover_path

    def show_play(self, _widget, *_unused):
        self.play_revealer.set_reveal_child(True)
        self.title_revealer.set_reveal_child(False)

    def hide_play(self, _widget, *_unused):
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(False)
            self.title_revealer.set_reveal_child(True)

    def launch_game(self, _widget, *_unused):
        self.win.set_active_game(None, None, self.game_id)
        self.win.get_application().on_launch_game_action(None)

    def cover_button_clicked(self, _widget):
        if self.win.schema.get_boolean("cover-launches-game"):
            self.launch_game(None)
        else:
            self.win.show_details_view(None, self.game_id)

    def play_button_clicked(self, _widget):
        if self.win.schema.get_boolean("cover-launches-game"):
            self.win.show_details_view(None, self.game_id)
        else:
            self.launch_game(None)

    def set_play_label(self):
        if self.win.schema.get_boolean("cover-launches-game"):
            self.play_button.set_label(_("Details"))
        else:
            self.play_button.set_label(_("Play"))

    def schema_changed(self, _settings, key):
        if key == "cover-launches-game":
            self.set_play_label()

    def set_loading(self, state):
        self.loading += state
        loading = self.loading > 0

        self.cover.set_opacity(int(not loading))
        self.spinner.set_spinning(loading)
