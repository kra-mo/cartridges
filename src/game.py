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

import logging
import os
import shlex
import subprocess
from pathlib import Path
from time import time

from gi.repository import Adw, GObject, Gtk

from src import shared  # pylint: disable=no-name-in-module


# pylint: disable=too-many-instance-attributes
@Gtk.Template(resource_path=shared.PREFIX + "/gtk/game.ui")
class Game(Gtk.Box):
    __gtype_name__ = "Game"

    title = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    play_revealer = Gtk.Template.Child()
    menu_revealer = Gtk.Template.Child()
    game_options = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()

    loading = 0
    filtered = False

    added = None
    executable = None
    game_id = None
    source = None
    hidden = False
    last_played = 0
    name = None
    developer = None
    removed = False
    blacklisted = False
    game_cover = None
    version = 0

    def __init__(self, data, allow_side_effects=True, **kwargs):
        super().__init__(**kwargs)

        self.win = shared.win
        self.app = self.win.get_application()
        self.version = shared.SPEC_VERSION

        self.update_values(data)

        if allow_side_effects:
            self.win.games[self.game_id] = self

        self.set_play_icon()

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_contoller_motion)
        self.event_contoller_motion.connect("enter", self.toggle_play, False)
        self.event_contoller_motion.connect("leave", self.toggle_play, None, None)
        self.cover_button.connect("clicked", self.main_button_clicked, False)
        self.play_button.connect("clicked", self.main_button_clicked, True)

        shared.schema.connect("changed", self.schema_changed)

    def update_values(self, data):
        for key, value in data.items():
            setattr(self, key, value)

    def update(self):
        self.emit("update-ready", {})

    def save(self):
        self.emit("save-ready", {})

    def create_toast(self, title, action=None):
        toast = Adw.Toast.new(title.format(self.name))
        toast.set_priority(Adw.ToastPriority.HIGH)

        if action:
            toast.set_button_label(_("Undo"))
            toast.connect("button-clicked", self.win.on_undo_action, self, action)

            if (self, action) in self.win.toasts.keys():
                # Dismiss the toast if there already is one
                self.win.toasts[(self, action)].dismiss()

            self.win.toasts[(self, action)] = toast

        self.win.toast_overlay.add_toast(toast)

    def launch(self):
        self.last_played = int(time())
        self.save()
        self.update()

        string = (
            self.executable
            if isinstance(self.executable, str)
            else shlex.join(self.executable)
        )

        args = (
            "flatpak-spawn --host /bin/sh -c " + shlex.quote(string)  # Flatpak
            if os.getenv("FLATPAK_ID") == shared.APP_ID
            else string  # Others
        )

        logging.info("Starting %s: %s", self.name, str(args))
        # pylint: disable=consider-using-with
        subprocess.Popen(
            args,
            cwd=Path.home(),
            shell=True,
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

        if shared.schema.get_boolean("exit-after-launch"):
            self.app.quit()

        # The variable is the title of the game
        self.create_toast(_("{} launched"))

    def toggle_hidden(self, toast=True):
        self.hidden = not self.hidden
        self.save()
        self.update()

        if self.win.stack.get_visible_child() == self.win.details_view:
            self.win.on_go_back_action()

        if toast:
            self.create_toast(
                # The variable is the title of the game
                (_("{} hidden") if self.hidden else _("{} unhidden")).format(self.name),
                "hide",
            )

    def remove_game(self):
        # Add "removed=True" to the game properties so it can be deleted on next init
        self.removed = True
        self.save()
        self.update()

        if self.win.stack.get_visible_child() == self.win.details_view:
            self.win.on_go_back_action()

        # The variable is the title of the game
        self.create_toast(_("{} removed").format(self.name), "remove")

    def set_loading(self, state):
        self.loading += state
        loading = self.loading > 0

        self.cover.set_opacity(int(not loading))
        self.spinner.set_spinning(loading)

    def get_cover_path(self):
        cover_path = shared.covers_dir / f"{self.game_id}.gif"
        if cover_path.is_file():
            return cover_path

        cover_path = shared.covers_dir / f"{self.game_id}.tiff"
        if cover_path.is_file():
            return cover_path

        return None

    def toggle_play(self, _widget, _prop1, _prop2, state=True):
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(not state)
            self.menu_revealer.set_reveal_child(not state)

    def main_button_clicked(self, _widget, button):
        if shared.schema.get_boolean("cover-launches-game") ^ button:
            self.launch()
        else:
            self.win.show_details_view(self)

    def set_play_icon(self):
        self.play_button.set_icon_name(
            "help-about-symbolic"
            if shared.schema.get_boolean("cover-launches-game")
            else "media-playback-start-symbolic"
        )

    def schema_changed(self, _settings, key):
        if key == "cover-launches-game":
            self.set_play_icon()

    @GObject.Signal(name="update-ready", arg_types=[object])
    def update_ready(self, _additional_data) -> None:
        """Signal emitted when the game needs updating"""

    @GObject.Signal(name="save-ready", arg_types=[object])
    def save_ready(self, _additional_data) -> None:
        """Signal emitted when the game needs saving"""
