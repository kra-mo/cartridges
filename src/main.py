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
import lzma
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, Gtk

from src import shared
from src.details_window import DetailsWindow
from src.game import Game
from src.importer.importer import Importer
from src.importer.sources.bottles_source import BottlesSource
from src.importer.sources.flatpak_source import FlatpakSource
from src.importer.sources.heroic_source import HeroicSource
from src.importer.sources.itch_source import ItchSource
from src.importer.sources.legendary_source import LegendarySource
from src.importer.sources.lutris_source import LutrisSource
from src.importer.sources.retroarch_source import RetroarchSource
from src.importer.sources.steam_source import SteamSource
from src.logging.setup import log_system_info, setup_logging
from src.preferences import PreferencesWindow
from src.store.managers.cover_manager import CoverManager
from src.store.managers.display_manager import DisplayManager
from src.store.managers.file_manager import FileManager
from src.store.managers.sgdb_manager import SGDBManager
from src.store.managers.steam_api_manager import SteamAPIManager
from src.store.store import Store
from src.utils.migrate_files_v1_to_v2 import migrate_files_v1_to_v2
from src.window import CartridgesWindow


class CartridgesApplication(Adw.Application):
    state = shared.AppState.DEFAULT
    win = None

    def __init__(self):
        shared.store = Store()
        super().__init__(
            application_id=shared.APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):  # pylint: disable=arguments-differ
        """Called on app creation"""

        setup_logging()
        log_system_info()

        if os.name == "nt":
            migrate_files_v1_to_v2()

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

        # Load games from disk
        shared.store.add_manager(FileManager(), False)
        shared.store.add_manager(DisplayManager())
        self.state = shared.AppState.LOAD_FROM_DISK
        self.load_games_from_disk()
        self.state = shared.AppState.DEFAULT
        self.win.create_source_rows()

        # Add rest of the managers for game imports
        shared.store.add_manager(CoverManager())
        shared.store.add_manager(SteamAPIManager())
        shared.store.add_manager(SGDBManager())
        shared.store.toggle_manager_in_pipelines(FileManager, True)

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
                ("show_sidebar", ("F9",), self.win),
                ("show_hidden", ("<primary>h",), self.win),
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
        if shared.games_dir.is_dir():
            for game_file in shared.games_dir.iterdir():
                data = json.load(game_file.open())
                game = Game(data)
                shared.store.add_game(game, {"skip_save": True})

    def get_source_name(self, source_id):
        return globals()[f'{source_id.split("_")[0].title()}Source'].name

    def on_about_action(self, *_args):
        # Get the debug info from the log files
        debug_str = ""
        for i, path in enumerate(shared.log_files):
            # Add a horizontal line between runs
            if i > 0:
                debug_str += "─" * 37 + "\n"
            # Add the run's logs
            log_file = (
                lzma.open(path, "rt", encoding="utf-8")
                if path.name.endswith(".xz")
                else open(path, "r", encoding="utf-8")
            )
            debug_str += log_file.read()
            log_file.close()

        about = Adw.AboutWindow.new_from_appdata(
            shared.PREFIX + "/" + shared.APP_ID + ".metainfo.xml", shared.VERSION
        )
        about.set_transient_for(self.win)
        about.set_developers(
            (
                "kramo https://kramo.hu",
                "Geoffrey Coulaud https://geoffrey-coulaud.fr",
                "Rilic https://rilic.red",
                "Arcitec https://github.com/Arcitec",
                "Paweł Lidwin https://github.com/imLinguin",
                "Domenico https://github.com/Domefemia",
                "Rafael Mardojai CM https://mardojai.com",
            )
        )
        about.set_designers(("kramo https://kramo.hu",))
        about.set_copyright("© 2022-2023 kramo")
        # Translators: Replace this with your name for it to show up in the about window
        about.set_translator_credits = (_("translator_credits"),)
        about.set_debug_info(debug_str)
        about.set_debug_info_filename("cartridges.log")
        about.add_legal_section(
            "Steam Branding",
            "© 2023 Valve Corporation",
            Gtk.License.CUSTOM,
            "Steam and the Steam logo are trademarks and/or registered trademarks of Valve Corporation in the U.S. and/or other countries.",  # pylint: disable=line-too-long
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

        return win

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

        if shared.schema.get_boolean("flatpak"):
            importer.add_source(FlatpakSource())

        if shared.schema.get_boolean("itch"):
            importer.add_source(ItchSource())

        if shared.schema.get_boolean("legendary"):
            importer.add_source(LegendarySource())

        if shared.schema.get_boolean("retroarch"):
            importer.add_source(RetroarchSource())

        importer.run()

    def on_remove_game_action(self, *_args):
        self.win.active_game.remove_game()

    def on_remove_game_details_view_action(self, *_args):
        if self.win.navigation_view.get_visible_page() == self.win.details_page:
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


def main(_version):
    """App entry point"""
    app = CartridgesApplication()
    return app.run(sys.argv)
