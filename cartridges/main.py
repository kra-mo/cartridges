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
import shlex
import sys
from typing import Any, Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, Gtk

from cartridges import shared
from cartridges.details_window import DetailsWindow
from cartridges.game import Game
from cartridges.importer.bottles_source import BottlesSource
from cartridges.importer.desktop_source import DesktopSource
from cartridges.importer.flatpak_source import FlatpakSource
from cartridges.importer.heroic_source import HeroicSource
from cartridges.importer.importer import Importer
from cartridges.importer.itch_source import ItchSource
from cartridges.importer.legendary_source import LegendarySource
from cartridges.importer.lutris_source import LutrisSource
from cartridges.importer.retroarch_source import RetroarchSource
from cartridges.importer.steam_source import SteamSource
from cartridges.logging.setup import log_system_info, setup_logging
from cartridges.preferences import PreferencesWindow
from cartridges.store.managers.cover_manager import CoverManager
from cartridges.store.managers.display_manager import DisplayManager
from cartridges.store.managers.file_manager import FileManager
from cartridges.store.managers.sgdb_manager import SgdbManager
from cartridges.store.managers.steam_api_manager import SteamAPIManager
from cartridges.store.store import Store
from cartridges.utils.migrate_files_v1_to_v2 import migrate_files_v1_to_v2
from cartridges.utils.run_executable import run_executable
from cartridges.window import CartridgesWindow


class CartridgesApplication(Adw.Application):
    state = shared.AppState.DEFAULT
    win: CartridgesWindow
    init_search_term: Optional[str] = None

    def __init__(self) -> None:
        shared.store = Store()
        super().__init__(
            application_id=shared.APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )

    def do_activate(self) -> None:  # pylint: disable=arguments-differ
        """Called on app creation"""

        setup_logging()
        log_system_info()

        if os.name == "nt":
            migrate_files_v1_to_v2()

        # Set fallback icon-name
        Gtk.Window.set_default_icon_name(shared.APP_ID)

        # Create the main window
        win = self.props.active_window  # pylint: disable=no-member
        if not win:
            shared.win = win = CartridgesWindow(application=self)

        # Save window geometry
        shared.state_schema.bind(
            "width", shared.win, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        shared.state_schema.bind(
            "height", shared.win, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        shared.state_schema.bind(
            "is-maximized", shared.win, "maximized", Gio.SettingsBindFlags.DEFAULT
        )

        # Load games from disk
        shared.store.add_manager(FileManager(), False)
        shared.store.add_manager(DisplayManager())
        self.state = shared.AppState.LOAD_FROM_DISK
        self.load_games_from_disk()
        self.state = shared.AppState.DEFAULT
        shared.win.create_source_rows()

        # Add rest of the managers for game imports
        shared.store.add_manager(CoverManager())
        shared.store.add_manager(SteamAPIManager())
        shared.store.add_manager(SgdbManager())
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
                ("show_sidebar", ("F9",), shared.win),
                ("show_hidden", ("<primary>h",), shared.win),
                ("go_to_parent", ("<alt>Up",), shared.win),
                ("go_home", ("<alt>Home",), shared.win),
                ("toggle_search", ("<primary>f",), shared.win),
                ("escape", ("Escape",), shared.win),
                ("undo", ("<primary>z",), shared.win),
                ("open_menu", ("F10",), shared.win),
                ("close", ("<primary>w",), shared.win),
            }
        )

        sort_action = Gio.SimpleAction.new_stateful(
            "sort_by", GLib.VariantType.new("s"), GLib.Variant("s", "a-z")
        )
        sort_action.connect("activate", shared.win.on_sort_action)
        shared.win.add_action(sort_action)
        shared.win.on_sort_action(
            sort_action, shared.state_schema.get_value("sort-mode")
        )

        if self.init_search_term:  # For command line activation
            shared.win.search_bar.set_search_mode(True)
            shared.win.search_entry.set_text(self.init_search_term)
            shared.win.search_entry.set_position(-1)

        shared.win.present()

    def do_command_line(self, command_line) -> int:
        for index, arg in enumerate(args := command_line.get_arguments()):
            if arg == "--search":
                try:
                    self.init_search_term = args[index + 1]
                except IndexError:
                    pass
                break

            if arg == "--launch":
                try:
                    game_id = args[index + 1]
                    data = json.load((shared.games_dir / (game_id + ".json")).open("r"))
                    executable = (
                        shlex.join(data["executable"])
                        if isinstance(data["executable"], list)
                        else data["executable"]
                    )
                    name = data["name"]

                    run_executable(executable)
                except (IndexError, KeyError, OSError, json.decoder.JSONDecodeError):
                    return 1

                notification = Gio.Notification.new(_("Cartridges"))
                notification.set_body(_("{} launched").format(name))
                self.send_notification(
                    "launch",
                    notification,
                )
                return 0
        self.activate()
        return 0

    def load_games_from_disk(self) -> None:
        if shared.games_dir.is_dir():
            for game_file in shared.games_dir.iterdir():
                try:
                    data = json.load(game_file.open())
                except (OSError, json.decoder.JSONDecodeError):
                    continue
                game = Game(data)
                shared.store.add_game(game, {"skip_save": True})

    def get_source_name(self, source_id: str) -> Any:
        if source_id == "all":
            name = _("All Games")
        elif source_id == "imported":
            name = _("Added")
        else:
            name = globals()[f'{source_id.split("_")[0].title()}Source'].name
        return name

    def on_about_action(self, *_args: Any) -> None:
        # Get the debug info from the log files
        debug_str = ""
        for index, path in enumerate(shared.log_files):
            # Add a horizontal line between runs
            if index > 0:
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
        about.set_transient_for(shared.win)
        about.set_developers(
            (
                "kramo https://kramo.hu",
                "Geoffrey Coulaud https://geoffrey-coulaud.fr",
                "Rilic https://rilic.red",
                "Arcitec https://github.com/Arcitec",
                "Paweł Lidwin https://github.com/imLinguin",
                "Domenico https://github.com/Domefemia",
                "Rafael Mardojai CM https://mardojai.com",
                "Clara Hobbs https://github.com/Ratfink",
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
        self,
        _action: Any = None,
        _parameter: Any = None,
        page_name: Optional[str] = None,
        expander_row: Optional[str] = None,
    ) -> CartridgesWindow:
        win = PreferencesWindow()
        if page_name:
            win.set_visible_page_name(page_name)
        if expander_row:
            getattr(win, expander_row).set_expanded(True)
        win.present()

        return win

    def on_launch_game_action(self, *_args: Any) -> None:
        shared.win.active_game.launch()

    def on_hide_game_action(self, *_args: Any) -> None:
        shared.win.active_game.toggle_hidden()

    def on_edit_game_action(self, *_args: Any) -> None:
        DetailsWindow(shared.win.active_game)

    def on_add_game_action(self, *_args: Any) -> None:
        DetailsWindow()

    def on_import_action(self, *_args: Any) -> None:
        shared.importer = Importer()

        if shared.schema.get_boolean("lutris"):
            shared.importer.add_source(LutrisSource())

        if shared.schema.get_boolean("steam"):
            shared.importer.add_source(SteamSource())

        if shared.schema.get_boolean("heroic"):
            shared.importer.add_source(HeroicSource())

        if shared.schema.get_boolean("bottles"):
            shared.importer.add_source(BottlesSource())

        if shared.schema.get_boolean("flatpak"):
            shared.importer.add_source(FlatpakSource())

        if shared.schema.get_boolean("desktop"):
            shared.importer.add_source(DesktopSource())

        if shared.schema.get_boolean("itch"):
            shared.importer.add_source(ItchSource())

        if shared.schema.get_boolean("legendary"):
            shared.importer.add_source(LegendarySource())

        if shared.schema.get_boolean("retroarch"):
            shared.importer.add_source(RetroarchSource())

        shared.importer.run()

    def on_remove_game_action(self, *_args: Any) -> None:
        shared.win.active_game.remove_game()

    def on_remove_game_details_view_action(self, *_args: Any) -> None:
        if shared.win.navigation_view.get_visible_page() == shared.win.details_page:
            self.on_remove_game_action()

    def search(self, uri: str) -> None:
        Gio.AppInfo.launch_default_for_uri(f"{uri}{shared.win.active_game.name}")

    def on_igdb_search_action(self, *_args: Any) -> None:
        self.search("https://www.igdb.com/search?type=1&q=")

    def on_sgdb_search_action(self, *_args: Any) -> None:
        self.search("https://www.steamgriddb.com/search/grids?term=")

    def on_protondb_search_action(self, *_args: Any) -> None:
        self.search("https://www.protondb.com/search?q=")

    def on_lutris_search_action(self, *_args: Any) -> None:
        self.search("https://lutris.net/games?q=")

    def on_hltb_search_action(self, *_args: Any) -> None:
        self.search("https://howlongtobeat.com/?q=")

    def on_quit_action(self, *_args: Any) -> None:
        self.quit()

    def create_actions(self, actions: set) -> None:
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


def main(_version: int) -> Any:
    """App entry point"""
    app = CartridgesApplication()
    return app.run(sys.argv)
