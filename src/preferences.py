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

from gi.repository import Adw, Gio, GLib, Gtk


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/preferences.ui")
class PreferencesWindow(Adw.PreferencesWindow):
    __gtype_name__ = "PreferencesWindow"

    page = Gtk.Template.Child()
    bottles_group = Gtk.Template.Child()

    exit_after_launch_switch = Gtk.Template.Child()
    import_epic_games_switch = Gtk.Template.Child()
    import_gog_games_switch = Gtk.Template.Child()
    import_sideload_games_switch = Gtk.Template.Child()

    steam_file_chooser_button = Gtk.Template.Child()
    steam_extra_file_chooser_button = Gtk.Template.Child()
    steam_clear_button = Gtk.Template.Child()
    steam_clear_button_revealer = Gtk.Template.Child()
    heroic_file_chooser_button = Gtk.Template.Child()
    bottles_file_chooser_button = Gtk.Template.Child()

    def __init__(self, parent_widget, **kwargs):
        super().__init__(**kwargs)

        self.set_transient_for(parent_widget)
        schema = parent_widget.schema
        schema.bind(
            "exit-after-launch",
            self.exit_after_launch_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        schema.bind(
            "heroic-import-epic",
            self.import_epic_games_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        schema.bind(
            "heroic-import-gog",
            self.import_gog_games_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )
        schema.bind(
            "heroic-import-sideload",
            self.import_sideload_games_switch,
            "active",
            Gio.SettingsBindFlags.DEFAULT,
        )

        filechooser = Gtk.FileDialog()

        def update_revealer():
            if schema.get_strv("steam-extra-dirs"):
                self.steam_clear_button_revealer.set_reveal_child(True)
            else:
                self.steam_clear_button_revealer.set_reveal_child(False)

        def set_steam_dir(_source, result, _unused):
            try:
                schema.set_string(
                    "steam-location",
                    filechooser.select_folder_finish(result).get_path(),
                )
            except GLib.GError:
                pass

        def add_steam_dir(_source, result, _unused):
            try:
                value = schema.get_strv("steam-extra-dirs")
                value.append(filechooser.select_folder_finish(result).get_path())
                schema.set_strv("steam-extra-dirs", value)
            except GLib.GError:
                pass
            update_revealer()

        def clear_steam_dirs(*_unused):
            schema.set_strv("steam-extra-dirs", [])
            update_revealer()

        def set_heroic_dir(_source, result, _unused):
            try:
                schema.set_string(
                    "heroic-location",
                    filechooser.select_folder_finish(result).get_path(),
                )
            except GLib.GError:
                pass

        def set_bottles_dir(_source, result, _unused):
            try:
                schema.set_string(
                    "bottles-location",
                    filechooser.select_folder_finish(result).get_path(),
                )
            except GLib.GError:
                pass

        def choose_folder(_widget, function):
            filechooser.select_folder(parent_widget, None, function, None)

        update_revealer()

        self.steam_file_chooser_button.connect("clicked", choose_folder, set_steam_dir)
        self.steam_extra_file_chooser_button.connect(
            "clicked", choose_folder, add_steam_dir
        )
        self.steam_clear_button.connect("clicked", clear_steam_dirs)
        self.heroic_file_chooser_button.connect(
            "clicked", choose_folder, set_heroic_dir
        )
        self.bottles_file_chooser_button.connect(
            "clicked", choose_folder, set_bottles_dir
        )

        if os.name == "nt":
            self.page.remove(self.bottles_group)
