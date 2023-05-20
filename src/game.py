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
from pathlib import Path
from time import time

from gi.repository import Adw, Gio, GLib, Gtk

from .game_cover import GameCover


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/game.ui")
class Game(Gtk.Box):
    __gtype_name__ = "Game"

    title = Gtk.Template.Child()
    play_button = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    spinner = Gtk.Template.Child()
    cover_button = Gtk.Template.Child()
    menu_button = Gtk.Template.Child()
    play_revealer = Gtk.Template.Child()
    game_options = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()

    loading = 0
    filtered = False

    added = None
    executable = None
    game_id = None
    source = None
    hidden = None
    last_played = None
    name = None
    developer = None
    removed = None
    blacklisted = None
    game_cover = None

    def __init__(self, win, data, **kwargs):
        super().__init__(**kwargs)

        self.win = win
        self.app = win.get_application()

        self.update_values(data)

        self.win.games[self.game_id] = self

        self.set_play_icon()

        self.event_contoller_motion = Gtk.EventControllerMotion.new()
        self.add_controller(self.event_contoller_motion)
        self.event_contoller_motion.connect("enter", self.toggle_play, False)
        self.event_contoller_motion.connect("leave", self.toggle_play, None, None)

        self.cover_button.connect("clicked", self.main_button_clicked, False)
        self.play_button.connect("clicked", self.main_button_clicked, True)

        self.win.schema.connect("changed", self.schema_changed)

    def update(self):
        if self.get_parent():
            self.get_parent().get_parent().remove(self)
            if self.get_parent():
                self.get_parent().set_child()

        self.menu_button.set_menu_model(
            self.hidden_game_options if self.hidden else self.game_options
        )

        self.title.set_label(self.name)

        self.menu_button.get_popover().connect(
            "notify::visible", self.toggle_play, None
        )
        self.menu_button.get_popover().connect(
            "notify::visible", self.win.set_active_game, self
        )

        if self.game_id in self.win.game_covers:
            self.game_cover = self.win.game_covers[self.game_id]
            self.game_cover.add_picture(self.cover)
        else:
            self.game_cover = GameCover({self.cover}, self.get_cover_path())
            self.win.game_covers[self.game_id] = self.game_cover

        if (
            self.win.stack.get_visible_child() == self.win.details_view
            and self.win.active_game == self
        ):
            self.win.show_details_view(self)

        if not self.removed and not self.blacklisted:
            if self.hidden:
                self.win.hidden_library.append(self)
            else:
                self.win.library.append(self)
            self.get_parent().set_focusable(False)

        self.win.set_library_child()

    def update_values(self, data):
        for key, value in data.items():
            setattr(self, key, value)

    def save(self):
        self.win.games_dir.mkdir(parents=True, exist_ok=True)

        attrs = (
            "added",
            "executable",
            "game_id",
            "source",
            "hidden",
            "last_played",
            "name",
            "developer",
            "removed",
            "blacklisted",
        )

        # TODO: remove for 2.0
        attrs = list(attrs)
        if not self.removed:
            attrs.remove("removed")
        if not self.blacklisted:
            attrs.remove("blacklisted")

        json.dump(
            {attr: getattr(self, attr) for attr in attrs if attr},
            (self.win.games_dir / f"{self.game_id}.json").open("w"),
            indent=4,
            sort_keys=True,
        )

        self.update()

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

        argv = (
            ("flatpak-spawn", "--host", *self.executable)  # Flatpak
            if os.getenv("FLATPAK_ID") == "hu.kramo.Cartridges"
            else self.executable  # Others
        )

        GLib.spawn_async(
            argv, working_directory=str(Path.home()), flags=GLib.SpawnFlags.SEARCH_PATH
        )
        if Gio.Settings.new("hu.kramo.Cartridges").get_boolean("exit-after-launch"):
            self.app.quit()

        # The variable is the title of the game
        self.create_toast(_("{} launched"))

    def toggle_hidden(self, toast=True):
        self.hidden = not self.hidden
        self.save()

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
        cover_path = self.win.covers_dir / f"{self.game_id}.gif"
        if cover_path.is_file():
            return cover_path

        cover_path = self.win.covers_dir / f"{self.game_id}.tiff"
        if cover_path.is_file():
            return cover_path

        return None

    def toggle_play(self, _widget, _prop1, _prop2, state=True):
        if not self.menu_button.get_active():
            self.play_revealer.set_reveal_child(not state)

    def main_button_clicked(self, _widget, button):
        if self.win.schema.get_boolean("cover-launches-game") ^ button:
            self.launch()
        else:
            self.win.show_details_view(self)

    def set_play_icon(self):
        self.play_button.set_icon_name(
            "help-about-symbolic"
            if self.win.schema.get_boolean("cover-launches-game")
            else "media-playback-start-symbolic"
        )

    def schema_changed(self, _settings, key):
        if key == "cover-launches-game":
            self.set_play_icon()
