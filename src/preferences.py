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
from shutil import move

from gi.repository import Adw, Gio, GLib, Gtk

from .bottles_importer import bottles_installed
from .create_dialog import create_dialog
from .get_games import get_games
from .heroic_importer import heroic_installed
from .itch_importer import itch_installed
from .lutris_importer import lutris_cache_exists, lutris_installed
from .save_game import save_game
from .steam_importer import steam_installed


class ImportPreferences:
    def __init__(
        self,
        win,
        source_id,
        name,
        check_func,
        expander_row,
        file_chooser_button,
        config=False,
    ):
        def set_dir(_source, result, _unused):
            try:
                path = Path(win.file_chooser.select_folder_finish(result).get_path())
            except GLib.GError:
                return

            def response(widget, response):
                if response == "choose_folder":
                    win.choose_folder(widget, set_dir)

            if not check_func(win, path):
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
            expander_row,
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )

        file_chooser_button.connect("clicked", win.choose_folder, set_dir)


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
    lutris_steam_switch = Gtk.Template.Child()

    heroic_expander_row = Gtk.Template.Child()
    heroic_file_chooser_button = Gtk.Template.Child()
    heroic_epic_switch = Gtk.Template.Child()
    heroic_gog_switch = Gtk.Template.Child()
    heroic_sideloaded_switch = Gtk.Template.Child()

    bottles_expander_row = Gtk.Template.Child()
    bottles_file_chooser_button = Gtk.Template.Child()

    itch_expander_row = Gtk.Template.Child()
    itch_file_chooser_button = Gtk.Template.Child()

    sgdb_key_group = Gtk.Template.Child()
    sgdb_key_entry_row = Gtk.Template.Child()
    sgdb_download_switch = Gtk.Template.Child()
    sgdb_prefer_switch = Gtk.Template.Child()
    sgdb_animated_switch = Gtk.Template.Child()

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
        shortcut_controller = Gtk.ShortcutController()
        shortcut_controller.add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<primary>z"),
                Gtk.CallbackAction.new(self.undo_remove_all),
            )
        )
        self.add_controller(shortcut_controller)
        self.removed_games = []

        # General
        self.schema.bind(
            "exit-after-launch",
            self.exit_after_launch_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.schema.bind(
            "cover-launches-game",
            self.cover_launches_game_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.schema.bind(
            "high-quality-images",
            self.high_quality_images_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self.remove_all_games_button.connect("clicked", self.remove_all_games)

        # Steam
        ImportPreferences(
            self,
            "steam",
            "Steam",
            steam_installed,
            self.steam_expander_row,
            self.steam_file_chooser_button,
        )

        def update_revealer():
            if self.schema.get_strv("steam-extra-dirs"):
                self.steam_clear_button_revealer.set_reveal_child(True)
            else:
                self.steam_clear_button_revealer.set_reveal_child(False)

        def add_steam_dir(_source, result, _unused):
            try:
                value = self.schema.get_strv("steam-extra-dirs")
                value.append(self.file_chooser.select_folder_finish(result).get_path())
                self.schema.set_strv("steam-extra-dirs", value)
            except GLib.GError:
                return
            update_revealer()

        def clear_steam_dirs(*_unused):
            self.schema.set_strv("steam-extra-dirs", [])
            update_revealer()

        update_revealer()

        self.steam_extra_file_chooser_button.connect(
            "clicked", self.choose_folder, add_steam_dir
        )
        self.steam_clear_button.connect("clicked", clear_steam_dirs)

        # Lutris
        ImportPreferences(
            self,
            "lutris",
            "Lutris",
            lutris_installed,
            self.lutris_expander_row,
            self.lutris_file_chooser_button,
        )
        self.schema.bind(
            "lutris-import-steam",
            self.lutris_steam_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        def set_cache_dir(_source, result, _unused):
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

        if os.name == "nt":
            self.sources_group.remove(self.lutris_expander_row)

        # Heroic
        ImportPreferences(
            self,
            "heroic",
            "Heroic",
            heroic_installed,
            self.heroic_expander_row,
            self.heroic_file_chooser_button,
            True,
        )

        self.schema.bind(
            "heroic-import-epic",
            self.heroic_epic_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.schema.bind(
            "heroic-import-gog",
            self.heroic_gog_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        self.schema.bind(
            "heroic-import-sideload",
            self.heroic_sideloaded_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        # Bottles
        ImportPreferences(
            self,
            "bottles",
            "Bottles",
            bottles_installed,
            self.bottles_expander_row,
            self.bottles_file_chooser_button,
        )

        if os.name == "nt":
            self.sources_group.remove(self.bottles_expander_row)

        # itch
        ImportPreferences(
            self,
            "itch",
            "itch",
            itch_installed,
            self.itch_expander_row,
            self.itch_file_chooser_button,
            True,
        )

        # SteamGridDB
        self.schema.bind(
            "sgdb",
            self.sgdb_download_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self.schema.bind(
            "sgdb-prefer",
            self.sgdb_prefer_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        self.schema.bind(
            "sgdb-animated",
            self.sgdb_animated_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        def sgdb_key_changed(_widget):
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

    def choose_folder(self, _widget, function):
        self.file_chooser.select_folder(self.win, None, function, None)

    def undo_remove_all(self, _widget, _unused):
        deleted_covers_dir = self.win.cache_dir / "cartridges" / "deleted_covers"

        for game_id in self.removed_games:
            data = get_games(self.win, [game_id])[game_id]
            if "removed" in data:
                data.pop("removed")
                save_game(self.win, data)

                cover_path = deleted_covers_dir / f"{game_id}.tiff"
                if not cover_path.is_file():
                    cover_path = deleted_covers_dir / f"{game_id}.gif"
                if not cover_path.is_file():
                    continue

                move(cover_path, self.win.covers_dir / cover_path.name)

        self.win.update_games(self.removed_games)
        self.removed_games = []
        self.toast.dismiss()

    def remove_all_games(self, _widget):
        deleted_covers_dir = self.win.cache_dir / "cartridges" / "deleted_covers"
        deleted_covers_dir.mkdir(parents=True, exist_ok=True)

        for game in get_games(self.win).values():
            if "removed" not in game:
                self.removed_games.append(game["game_id"])
                game["removed"] = True
                save_game(self.win, game)

                cover_path = self.win.games[game["game_id"]].get_cover_path()
                if not cover_path:
                    continue

                if cover_path.is_file():
                    move(cover_path, deleted_covers_dir / cover_path.name)

        self.win.update_games(self.win.games)
        if self.win.stack.get_visible_child() == self.win.details_view:
            self.win.on_go_back_action(None, None)

        self.add_toast(self.toast)
