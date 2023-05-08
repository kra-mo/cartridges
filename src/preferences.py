# preferences.py
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

import os
from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

# pylint: disable=unused-import
from .bottles_importer import bottles_installed
from .create_dialog import create_dialog
from .heroic_importer import heroic_installed
from .itch_importer import itch_installed
from .lutris_importer import lutris_cache_exists, lutris_installed
from .steam_importer import steam_installed


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/preferences.ui")
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    general_page = Gtk.Template.Child()
    import_page = Gtk.Template.Child()
    sgdb_page = Gtk.Template.Child()

    sources_group = Gtk.Template.Child()

    exit_after_launch_switch = Gtk.Template.Child()
    cover_launches_game_switch = Gtk.Template.Child()
    high_quality_images_switch = Gtk.Template.Child()
    remove_all_games_button = Gtk.Template.Child()

    steam_expander_row = Gtk.Template.Child()
    steam_file_chooser_button = Gtk.Template.Child()
    steam_extra_file_chooser_button = Gtk.Template.Child()
    steam_clear_button_revealer = Gtk.Template.Child()
    steam_clear_button = Gtk.Template.Child()

    lutris_expander_row = Gtk.Template.Child()
    lutris_file_chooser_button = Gtk.Template.Child()
    lutris_cache_file_chooser_button = Gtk.Template.Child()
    lutris_import_steam_switch = Gtk.Template.Child()

    heroic_expander_row = Gtk.Template.Child()
    heroic_file_chooser_button = Gtk.Template.Child()
    heroic_import_epic_switch = Gtk.Template.Child()
    heroic_import_gog_switch = Gtk.Template.Child()
    heroic_import_sideload_switch = Gtk.Template.Child()

    bottles_expander_row = Gtk.Template.Child()
    bottles_file_chooser_button = Gtk.Template.Child()

    itch_expander_row = Gtk.Template.Child()
    itch_file_chooser_button = Gtk.Template.Child()

    sgdb_key_group = Gtk.Template.Child()
    sgdb_key_entry_row = Gtk.Template.Child()
    sgdb_switch = Gtk.Template.Child()
    sgdb_prefer_switch = Gtk.Template.Child()
    sgdb_animated_switch = Gtk.Template.Child()

    removed_games = set()

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)
        self.schema = win.schema
        self.win = win
        self.file_chooser = Gtk.FileDialog()
        self.set_transient_for(win)

        self.toast = Adw.Toast.new(_("All games removed"))
        self.toast.set_button_label(_("Undo"))
        self.toast.connect("button-clicked", self.undo_remove_all, None)
        self.toast.set_priority(Adw.ToastPriority.HIGH)

        (shortcut_controller := Gtk.ShortcutController()).add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<primary>z"),
                Gtk.CallbackAction.new(self.undo_remove_all),
            )
        )
        self.add_controller(shortcut_controller)

        # General
        self.remove_all_games_button.connect("clicked", self.remove_all_games)

        # Steam
        self.create_preferences(self, "steam", "Steam")

        def update_revealer():
            if self.schema.get_strv("steam-extra-dirs"):
                self.steam_clear_button_revealer.set_reveal_child(True)
            else:
                self.steam_clear_button_revealer.set_reveal_child(False)

        def add_steam_dir(_source, result, *_args):
            try:
                value = self.schema.get_strv("steam-extra-dirs")
                value.append(self.file_chooser.select_folder_finish(result).get_path())
                self.schema.set_strv("steam-extra-dirs", value)
            except GLib.GError:
                return
            update_revealer()

        def clear_steam_dirs(*_args):
            self.schema.set_strv("steam-extra-dirs", [])
            update_revealer()

        update_revealer()

        self.steam_extra_file_chooser_button.connect(
            "clicked", self.choose_folder, add_steam_dir
        )
        self.steam_clear_button.connect("clicked", clear_steam_dirs)

        # Lutris
        self.create_preferences(self, "lutris", "Lutris")

        def set_cache_dir(_source, result, *_args):
            try:
                path = Path(self.file_chooser.select_folder_finish(result).get_path())
            except GLib.GError:
                return

            def response(widget, response):
                if response == "choose_folder":
                    self.choose_folder(widget, set_cache_dir)

            if not lutris_cache_exists(path).exists():
                create_dialog(
                    self.win,
                    _("Cache Not Found"),
                    _("Select the Lutris cache directory."),
                    "choose_folder",
                    _("Set Location"),
                ).connect("response", response)

        self.lutris_cache_file_chooser_button.connect(
            "clicked", self.choose_folder, set_cache_dir
        )

        # Heroic
        self.create_preferences(self, "heroic", "Heroic", True)

        # Bottles
        self.create_preferences(self, "bottles", "Bottles")

        # itch
        self.create_preferences(self, "itch", "itch", True)

        # SteamGridDB
        def sgdb_key_changed(*_args):
            self.schema.set_string("sgdb-key", self.sgdb_key_entry_row.get_text())

        self.sgdb_key_entry_row.set_text(self.schema.get_string("sgdb-key"))
        self.sgdb_key_entry_row.connect("changed", sgdb_key_changed)

        self.sgdb_key_group.set_description(
            _(
                "An API key is required to use SteamGridDB. You can generate one {}here{}."
            ).format(
                '<a href="https://www.steamgriddb.com/profile/preferences/api">', "</a>"
            )
        )

        # Switches
        self.bind_switches(
            (
                "exit-after-launch",
                "cover-launches-game",
                "high-quality-images",
                "lutris-import-steam",
                "heroic-import-epic",
                "heroic-import-gog",
                "heroic-import-sideload",
                "sgdb",
                "sgdb-prefer",
                "sgdb-animated",
            )
        )

        # Windows
        if os.name == "nt":
            self.sources_group.remove(self.lutris_expander_row)
            self.sources_group.remove(self.bottles_expander_row)

    def bind_switches(self, settings):
        for setting in settings:
            self.schema.bind(
                setting,
                getattr(self, f'{setting.replace("-", "_")}_switch'),
                "active",
                Gio.SettingsBindFlags.DEFAULT,
            )

    def choose_folder(self, _widget, function):
        self.file_chooser.select_folder(self.win, None, function, None)

    def undo_remove_all(self, *_args):
        for game in self.removed_games:
            game.removed = False
            game.save()

        self.removed_games = set()
        self.toast.dismiss()

    def remove_all_games(self, *_args):
        for game in self.win.games.values():
            if not game.removed:
                self.removed_games.add(game)

                game.removed = True
                game.save()

        if self.win.stack.get_visible_child() == self.win.details_view:
            self.win.on_go_back_action()

        self.add_toast(self.toast)

    def create_preferences(self, win, source_id, name, config=False):
        def set_dir(_source, result, *_args):
            try:
                path = Path(win.file_chooser.select_folder_finish(result).get_path())
            except GLib.GError:
                return

            def response(widget, response):
                if response == "choose_folder":
                    win.choose_folder(widget, set_dir)

            if not globals()[f"{source_id}_installed"](win, path):
                create_dialog(
                    win,
                    _("Installation Not Found"),
                    # The variable is the name of the game launcher
                    _("Select the {} configuration directory.").format(name) if config
                    # The variable is the name of the game launcher
                    else _("Select the {} data directory.").format(name),
                    "choose_folder",
                    _("Set Location"),
                ).connect("response", response)

        win.schema.bind(
            source_id,
            getattr(win, f"{source_id}_expander_row"),
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )

        getattr(win, f"{source_id}_file_chooser_button").connect(
            "clicked", win.choose_folder, set_dir
        )
