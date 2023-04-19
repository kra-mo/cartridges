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

import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, Gtk

from .bottles_importer import bottles_importer
from .create_details_window import create_details_window
from .heroic_importer import heroic_importer
from .importer import Importer
from .itch_importer import itch_importer
from .lutris_importer import lutris_importer
from .preferences import PreferencesWindow
from .steam_importer import steam_importer
from .window import CartridgesWindow


class CartridgesApplication(Adw.Application):
    win = None

    def __init__(self):
        super().__init__(
            application_id="hu.kramo.Cartridges", flags=Gio.ApplicationFlags.FLAGS_NONE
        )

    def do_activate(self):  # pylint: disable=arguments-differ
        # Create the main window
        self.win = self.props.active_window  # pylint: disable=no-member
        if not self.win:
            self.win = CartridgesWindow(application=self)

        # Save window geometry
        state_settings = Gio.Settings(schema_id="hu.kramo.Cartridge.State")
        state_settings.bind(
            "width", self.win, "default-width", Gio.SettingsBindFlags.DEFAULT
        )
        state_settings.bind(
            "height", self.win, "default-height", Gio.SettingsBindFlags.DEFAULT
        )
        state_settings.bind(
            "is-maximized", self.win, "maximized", Gio.SettingsBindFlags.DEFAULT
        )

        self.win.present()

        # Create actions
        self.create_actions(
            {
                (self, "quit", ("<primary>q",)),
                (self, "about", None),
                (self, "preferences", ("<primary>comma",)),
                (self, "launch_game", None),
                (self, "hide_game", None),
                (self, "edit_game", None),
                (self, "add_game", ("<primary>n",)),
                (self, "import", ("<primary>i",)),
                (self, "remove_game_details_view", ("Delete",)),
                (self, "remove_game", None),
                (self, "igdb_search", None),
                (self, "sgdb_search", None),
                (self, "protondb_search", None),
                (self, "lutris_search", None),
                (self, "hltb_search", None),
                (self.win, "show_hidden", ("<primary>h",)),
                (self.win, "go_back", ("<alt>Left",)),
                (self.win, "go_to_parent", ("<alt>Up",)),
                (self.win, "toggle_search", ("<primary>f",)),
                (self.win, "escape", ("Escape",)),
                (self.win, "undo", ("<primary>z",)),
                (self.win, "open_menu", ("F10",)),
            }
        )

        sort_action = Gio.SimpleAction.new_stateful(
            "sort_by", GLib.VariantType.new("s"), GLib.Variant("s", "a-z")
        )
        sort_action.connect("activate", self.win.on_sort_action)
        self.win.add_action(sort_action)
        self.win.on_sort_action(sort_action, state_settings.get_value("sort-mode"))

    def on_about_action(self, _widget, _callback=None):
        about = Adw.AboutWindow(
            transient_for=self.win,
            application_name=_("Cartridges"),
            application_icon="hu.kramo.Cartridges",
            developer_name="kramo",
            version="1.4",
            developers=[
                "kramo https://kramo.hu",
                "Paweł Lidwin https://github.com/imLinguin",
                "Domenico https://github.com/Domefemia",
                "Bananaman https://github.com/Bananaman",
                "Geoffrey Coulaud https://geoffrey-coulaud.fr",
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
        self, _widget, _callback=None, page_name=None, expander_row=None
    ):
        win = PreferencesWindow(self.win)
        if page_name:
            win.set_visible_page_name(page_name)
        if expander_row:
            getattr(win, expander_row).set_expanded(True)
        win.present()

    def on_launch_game_action(self, _widget=None, _callback=None):
        self.win.games[self.win.active_game_id].launch()

    def on_hide_game_action(
        self, _widget=None, _callback=None, game_id=None, toast=True
    ):
        self.win.games[game_id or self.win.active_game_id].toggle_hidden(toast)

    def on_edit_game_action(self, _widget, _callback=None):
        create_details_window(self.win, self.win.active_game_id)

    def on_add_game_action(self, _widget, _callback=None):
        create_details_window(self.win)

    def on_import_action(self, _widget, _callback=None):
        self.win.importer = Importer(self.win)

        self.win.importer.blocker = True

        if self.win.schema.get_boolean("steam"):
            steam_importer(self.win)

        if self.win.schema.get_boolean("lutris"):
            lutris_importer(self.win)

        if self.win.schema.get_boolean("heroic"):
            heroic_importer(self.win)

        if self.win.schema.get_boolean("bottles"):
            bottles_importer(self.win)

        if self.win.schema.get_boolean("itch"):
            itch_importer(self.win)

        self.win.importer.blocker = False

        if self.win.importer.import_dialog.is_visible and self.win.importer.queue == 0:
            self.win.importer.queue = 1
            self.win.importer.save_game()

    def on_remove_game_action(self, _widget=None, _callback=None):
        self.win.games[self.win.active_game_id].remove_game()

    def on_remove_game_details_view_action(self, _widget, _callback=None):
        if self.win.stack.get_visible_child() == self.win.details_view:
            self.on_remove_game_action()

    def on_quit_action(self, _widget, _callback=None):
        self.quit()

    def search(self, uri):
        Gio.AppInfo.launch_default_for_uri(
            f"{uri}{self.win.games[self.win.active_game_id].name}"
        )

    def on_igdb_search_action(self, _widget, _callback=None):
        self.search("https://www.igdb.com/search?type=1&q=")

    def on_sgdb_search_action(self, _widget, _callback=None):
        self.search("https://www.steamgriddb.com/search/grids?term=")

    def on_protondb_search_action(self, _widget, _callback=None):
        self.search("https://www.protondb.com/search?q=")

    def on_lutris_search_action(self, _widget, _callback=None):
        self.search("https://lutris.net/games?q=")

    def on_hltb_search_action(self, _widget, _callback=None):
        self.search("https://howlongtobeat.com/?q=")

    def create_actions(self, actions):
        for action in actions:
            simple_action = Gio.SimpleAction.new(action[1], None)
            simple_action.connect(
                "activate", getattr(action[0], f"on_{action[1]}_action")
            )
            if action[2]:
                self.set_accels_for_action(
                    f"app.{action[1]}" if action[0] == self else f"win.{action[1]}",
                    action[2],
                )

            action[0].add_action(simple_action)


def main(version):  # pylint: disable=unused-argument
    app = CartridgesApplication()
    return app.run(sys.argv)
