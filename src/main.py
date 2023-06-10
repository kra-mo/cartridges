# main.py
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
import logging
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, Gtk

from src import shared  # pylint: disable=no-name-in-module
from src.details_window import DetailsWindow
from src.game import Game
from src.importer.importer import Importer
from src.importer.sources.bottles_source import BottlesSource
from src.importer.sources.heroic_source import HeroicSource
from src.importer.sources.itch_source import ItchSource
from src.importer.sources.legendary_source import LegendarySource
from src.importer.sources.lutris_source import LutrisSource
from src.importer.sources.steam_source import SteamSource
from src.preferences import PreferencesWindow
from src.store.managers.display_manager import DisplayManager
from src.store.managers.file_manager import FileManager
from src.store.managers.itch_cover_manager import ItchCoverManager
from src.store.managers.local_cover_manager import LocalCoverManager
from src.store.managers.sgdb_manager import SGDBManager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.store.store import Store
from src.window import CartridgesWindow


class CartridgesApplication(Adw.Application):
    win = None

    def __init__(self):
        super().__init__(
            application_id=shared.APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):  # pylint: disable=arguments-differ
        """Called on app creation"""

        # Set fallback icon-name
        Gtk.Window.set_default_icon_name(shared.APP_ID)

        # Create the main window
        self.win = self.props.active_window  # pylint: disable=no-member
        if not self.win:
            shared.win = self.win = CartridgesWindow(application=self)

        # Save window geometry
        shared.state_schema.bind(
            "width", self.win, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        shared.state_schema.bind(
            "height", self.win, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        shared.state_schema.bind(
            "is-maximized", self.win, "maximized", Gio.SettingsBindFlags.DEFAULT
        )

        # Create the games store ready to load games from disk
        if not shared.store:
            shared.store = Store()
            shared.store.add_manager(DisplayManager())

        self.load_games_from_disk()

        # Add rest of the managers for game imports
        shared.store.add_manager(LocalCoverManager())
        shared.store.add_manager(SteamAPIManager())
        shared.store.add_manager(ItchCoverManager())
        shared.store.add_manager(SGDBManager())
        shared.store.add_manager(FileManager())

        # Create actions
        self.create_actions(
            {
                ("quit", ("<primary>q",)),
                ("about",),
                ("preferences", ("<primary>comma",)),
                ("launch_game",),
                ("hide_game",),
                ("edit_game",),
                ("add_game", ("<primary>n",)),
                ("import", ("<primary>i",)),
                ("remove_game_details_view", ("Delete",)),
                ("remove_game",),
                ("igdb_search",),
                ("sgdb_search",),
                ("protondb_search",),
                ("lutris_search",),
                ("hltb_search",),
                ("show_hidden", ("<primary>h",), self.win),
                ("go_back", ("<alt>Left",), self.win),
                ("go_to_parent", ("<alt>Up",), self.win),
                ("go_home", ("<alt>Home",), self.win),
                ("toggle_search", ("<primary>f",), self.win),
                ("escape", ("Escape",), self.win),
                ("undo", ("<primary>z",), self.win),
                ("open_menu", ("F10",), self.win),
                ("close", ("<primary>w",), self.win),
            }
        )

        sort_action = Gio.SimpleAction.new_stateful(
            "sort_by", GLib.VariantType.new("s"), GLib.Variant("s", "a-z")
        )
        sort_action.connect("activate", self.win.on_sort_action)
        self.win.add_action(sort_action)
        self.win.on_sort_action(sort_action, shared.state_schema.get_value("sort-mode"))

        self.win.present()

    def load_games_from_disk(self):
        if shared.games_dir.exists():
            for game_file in shared.games_dir.iterdir():
                data = json.load(game_file.open())
                game = Game(data, allow_side_effects=False)
                shared.store.add_game(game, tuple())

    def on_about_action(self, *_args):
        about = Adw.AboutWindow(
            transient_for=self.win,
            application_name=_("Cartridges"),
            application_icon=shared.APP_ID,
            developer_name="kramo",
            version=shared.VERSION,
            developers=[
                "kramo https://kramo.hu",
                "Arcitec https://github.com/Arcitec",
                "Domenico https://github.com/Domefemia",
                "Geoffrey Coulaud https://geoffrey-coulaud.fr",
                "Paweł Lidwin https://github.com/imLinguin",
                "Rafael Mardojai CM https://mardojai.com",
            ],
            designers=("kramo https://kramo.hu",),
            copyright="© 2022-2023 kramo",
            license_type=Gtk.License.GPL_3_0,
            issue_url="https://github.com/kra-mo/cartridges/issues/new",
            website="https://github.com/kra-mo/cartridges",
            # Translators: Replace this with your name for it to show up in the about window
            translator_credits=_("translator_credits"),
        )
        about.present()

    def on_preferences_action(
        self, _action=None, _parameter=None, page_name=None, expander_row=None
    ):
        win = PreferencesWindow()
        if page_name:
            win.set_visible_page_name(page_name)
        if expander_row:
            getattr(win, expander_row).set_expanded(True)
        win.present()

    def on_launch_game_action(self, *_args):
        self.win.active_game.launch()

    def on_hide_game_action(self, *_args):
        self.win.active_game.toggle_hidden()

    def on_edit_game_action(self, *_args):
        DetailsWindow(self.win.active_game)

    def on_add_game_action(self, *_args):
        DetailsWindow()

    def on_import_action(self, *_args):
        importer = Importer()

        if shared.schema.get_boolean("lutris"):
            importer.add_source(LutrisSource())

        if shared.schema.get_boolean("steam"):
            importer.add_source(SteamSource())

        if shared.schema.get_boolean("heroic"):
            importer.add_source(HeroicSource())

        if shared.schema.get_boolean("bottles"):
            importer.add_source(BottlesSource())

        if shared.schema.get_boolean("itch"):
            importer.add_source(ItchSource())

        if shared.schema.get_boolean("legendary"):
            importer.add_source(LegendarySource())

        importer.run()

    def on_remove_game_action(self, *_args):
        self.win.active_game.remove_game()

    def on_remove_game_details_view_action(self, *_args):
        if self.win.stack.get_visible_child() == self.win.details_view:
            self.on_remove_game_action()

    def search(self, uri):
        Gio.AppInfo.launch_default_for_uri(f"{uri}{self.win.active_game.name}")

    def on_igdb_search_action(self, *_args):
        self.search("https://www.igdb.com/search?type=1&q=")

    def on_sgdb_search_action(self, *_args):
        self.search("https://www.steamgriddb.com/search/grids?term=")

    def on_protondb_search_action(self, *_args):
        self.search("https://www.protondb.com/search?q=")

    def on_lutris_search_action(self, *_args):
        self.search("https://lutris.net/games?q=")

    def on_hltb_search_action(self, *_args):
        self.search("https://howlongtobeat.com/?q=")

    def on_quit_action(self, *_args):
        self.quit()

    def create_actions(self, actions):
        for action in actions:
            simple_action = Gio.SimpleAction.new(action[0], None)

            scope = action[2] if action[2:3] else self
            simple_action.connect("activate", getattr(scope, f"on_{action[0]}_action"))

            if action[1:2]:
                self.set_accels_for_action(
                    f"app.{action[0]}" if scope == self else f"win.{action[0]}",
                    action[1],
                )

            scope.add_action(simple_action)


def main(version):  # pylint: disable=unused-argument
    # Initiate logger
    # (silence debug info from external libraries)
    profile_base_log_level = "DEBUG" if shared.PROFILE == "development" else "WARNING"
    profile_lib_log_level = "INFO" if shared.PROFILE == "development" else "WARNING"
    base_log_level = os.environ.get("LOGLEVEL", profile_base_log_level).upper()
    lib_log_level = os.environ.get("LIBLOGLEVEL", profile_lib_log_level).upper()
    log_levels = {
        None: base_log_level,
        "PIL": lib_log_level,
        "urllib3": lib_log_level,
    }
    logging.basicConfig()
    for logger, level in log_levels.items():
        logging.getLogger(logger).setLevel(level)

    # Start app
    app = CartridgesApplication()
    return app.run(sys.argv)
