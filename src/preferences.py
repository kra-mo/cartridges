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
import re
from pathlib import Path

from gi.repository import Adw, Gio, GLib, Gtk

# pylint: disable=unused-import
from . import shared
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
    steam_action_row = Gtk.Template.Child()
    steam_file_chooser_button = Gtk.Template.Child()

    lutris_expander_row = Gtk.Template.Child()
    lutris_action_row = Gtk.Template.Child()
    lutris_file_chooser_button = Gtk.Template.Child()
    lutris_cache_action_row = Gtk.Template.Child()
    lutris_cache_file_chooser_button = Gtk.Template.Child()
    lutris_import_steam_switch = Gtk.Template.Child()

    heroic_expander_row = Gtk.Template.Child()
    heroic_action_row = Gtk.Template.Child()
    heroic_file_chooser_button = Gtk.Template.Child()
    heroic_import_epic_switch = Gtk.Template.Child()
    heroic_import_gog_switch = Gtk.Template.Child()
    heroic_import_sideload_switch = Gtk.Template.Child()

    bottles_expander_row = Gtk.Template.Child()
    bottles_action_row = Gtk.Template.Child()
    bottles_file_chooser_button = Gtk.Template.Child()

    itch_expander_row = Gtk.Template.Child()
    itch_action_row = Gtk.Template.Child()
    itch_file_chooser_button = Gtk.Template.Child()

    sgdb_key_group = Gtk.Template.Child()
    sgdb_key_entry_row = Gtk.Template.Child()
    sgdb_switch = Gtk.Template.Child()
    sgdb_switch_row = Gtk.Template.Child()
    sgdb_prefer_switch = Gtk.Template.Child()
    sgdb_animated_switch = Gtk.Template.Child()

    removed_games = set()

    # Whether to import after closing the window
    import_changed = False
    # Widgets and their properties to check whether to import after closing the window
    import_changed_widgets = {}

    def __init__(self, win, **kwargs):
        super().__init__(**kwargs)
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

            if lutris_cache_exists(self.win, path):
                self.import_changed = True
                self.set_subtitle(self, "lutris-cache")

            else:
                create_dialog(
                    self.win,
                    _("Cache Not Found"),
                    _("Select the Lutris cache directory."),
                    "choose_folder",
                    _("Set Location"),
                ).connect("response", response)

        self.set_subtitle(self, "lutris-cache")

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
            shared.schema.set_string("sgdb-key", self.sgdb_key_entry_row.get_text())

        self.sgdb_key_entry_row.set_text(shared.schema.get_string("sgdb-key"))
        self.sgdb_key_entry_row.connect("changed", sgdb_key_changed)

        self.sgdb_key_group.set_description(
            _(
                "An API key is required to use SteamGridDB. You can generate one {}here{}."
            ).format(
                '<a href="https://www.steamgriddb.com/profile/preferences/api">', "</a>"
            )
        )

        def set_sgdb_sensitive(widget):
            if not widget.get_text():
                shared.schema.set_boolean("sgdb", False)

            self.sgdb_switch_row.set_sensitive(widget.get_text())

        self.sgdb_key_entry_row.connect("changed", set_sgdb_sensitive)
        set_sgdb_sensitive(self.sgdb_key_entry_row)

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

        # Connect the switches that change the behavior of importing to set_import_changed
        self.connect_import_switches(
            (
                "lutris-import-steam",
                "heroic-import-epic",
                "heroic-import-gog",
                "heroic-import-sideload",
            )
        )

        # Windows
        if os.name == "nt":
            self.sources_group.remove(self.lutris_expander_row)
            self.sources_group.remove(self.bottles_expander_row)

        # When the user interacts with a widget that changes the behavior of importing,
        # Cartridges should automatically import upon closing the preferences window
        self.connect("close-request", self.check_import)

    def get_switch(self, setting):
        return getattr(self, f'{setting.replace("-", "_")}_switch')

    def bind_switches(self, settings):
        for setting in settings:
            shared.schema.bind(
                setting,
                self.get_switch(setting),
                "active",
                Gio.SettingsBindFlags.DEFAULT,
            )

    def connect_import_switches(self, settings):
        for setting in settings:
            self.get_switch(setting).connect("notify::active", self.set_import_changed)

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

    def set_subtitle(self, win, source_id):
        getattr(win, f'{source_id.replace("-", "_")}_action_row').set_subtitle(
            # Remove the path if the dir is picked via the Flatpak portal
            re.sub(
                "/run/user/\\d*/doc/......../",
                "",
                str(
                    Path(shared.schema.get_string(f"{source_id}-location")).expanduser()
                ),
            )
        )

    def create_preferences(self, win, source_id, name, config=False):
        def set_dir(_source, result, *_args):
            try:
                path = Path(win.file_chooser.select_folder_finish(result).get_path())
            except GLib.GError:
                return

            def response(widget, response):
                if response == "choose_folder":
                    win.choose_folder(widget, set_dir)

            if globals()[f"{source_id}_installed"](win, path):
                self.import_changed = True
                self.set_subtitle(win, source_id)

            else:
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

        self.set_subtitle(win, source_id)

        shared.schema.bind(
            source_id,
            getattr(win, f"{source_id}_expander_row"),
            "enable-expansion",
            Gio.SettingsBindFlags.DEFAULT,
        )

        getattr(win, f"{source_id}_file_chooser_button").connect(
            "clicked", win.choose_folder, set_dir
        )

        getattr(win, f"{source_id}_expander_row").connect(
            "notify::enable-expansion", self.set_import_changed
        )

    def set_import_changed(self, widget, param):
        if widget not in self.import_changed_widgets:
            self.import_changed = True
            self.import_changed_widgets[widget] = (
                param.name,
                not widget.get_property(param.name),
            )

    def check_import(self, *_args):
        # This checks whether any of the switches that did actually change their state
        # would have an effect on the outcome of the import action
        # and if they would, it initiates it.

        if self.import_changed and any(
            (value := widget.get_property(prop[0])) and value != prop[1]
            for widget, prop in self.import_changed_widgets.items()
        ):
            # The timeout is a hack to circumvent a GTK bug that I'm too lazy to report:
            # The window would stay darkened because of the import dialog for some reason
            GLib.timeout_add(1, self.win.get_application().on_import_action)
