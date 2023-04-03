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
import time

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

# pylint: disable=wrong-import-position
from gi.repository import Adw, Gio, GLib, Gtk

from .bottles_parser import bottles_parser
from .create_details_window import create_details_window
from .get_games import get_games
from .heroic_parser import heroic_parser
from .importer import Importer
from .lutris_parser import lutris_parser
from .preferences import PreferencesWindow
from .save_game import save_game
from .steam_parser import steam_parser
from .window import CartridgesWindow


class CartridgesApplication(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="hu.kramo.Cartridges", flags=Gio.ApplicationFlags.FLAGS_NONE
        )
        self.create_action("quit", self.on_quit_action, ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action(
            "preferences", self.on_preferences_action, ["<primary>comma"]
        )
        self.create_action("launch_game", self.on_launch_game_action)
        self.create_action("hide_game", self.on_hide_game_action)
        self.create_action("edit_details", self.on_edit_details_action)
        self.create_action("add_game", self.on_add_game_action, ["<primary>n"])
        self.create_action("import", self.on_import_action, ["<primary>i"])
        self.create_action("remove_game", self.on_remove_game_action)

        self.win = None

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

        # Create actions for the main window
        self.create_action(
            "show_hidden", self.win.on_show_hidden_action, ["<primary>h"], self.win
        )
        self.create_action(
            "go_back", self.win.on_go_back_action, ["<alt>Left"], self.win
        )
        self.create_action(
            "go_to_parent", self.win.on_go_to_parent_action, ["<alt>Up"], self.win
        )
        self.create_action(
            "toggle_search", self.win.on_toggle_search_action, ["<primary>f"], self.win
        )
        self.create_action("escape", self.win.on_escape_action, ["Escape"], self.win)
        self.create_action("undo", self.win.on_undo_action, ["<primary>z"], self.win)
        self.create_action("open_menu", self.win.on_open_menu_action, ["F10"], self.win)
        self.win.sort = Gio.SimpleAction.new_stateful(
            "sort_by", GLib.VariantType.new("s"), GLib.Variant("s", "a-z")
        )
        self.win.add_action(self.win.sort)
        self.win.sort.connect("activate", self.win.on_sort_action)
        self.win.on_sort_action(self.win.sort, state_settings.get_value("sort-mode"))

    def on_about_action(self, _widget, _callback=None):
        about = Adw.AboutWindow(
            transient_for=self.win,
            application_name=_("Cartridges"),
            application_icon="hu.kramo.Cartridges",
            developer_name="kramo",
            version="1.2.2",
            developers=[
                "kramo https://kramo.hu",
                "Paweł Lidwin https://github.com/imLinguin",
                "Bananaman https://github.com/Bananaman",
            ],
            designers=["kramo https://kramo.hu"],
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

    def on_launch_game_action(self, _widget, _callback=None):
        # Launch the game and update the last played value

        game_id = self.win.active_game_id

        data = get_games(self.win, [game_id])[game_id]
        data["last_played"] = int(time.time())
        save_game(self.win, data)

        self.win.games[game_id].launch()

        title = self.win.games[game_id].name
        # The variable is the title of the game
        toast = Adw.Toast.new(_("{} launched").format(title))
        toast.set_priority(Adw.ToastPriority.HIGH)
        self.win.toast_overlay.add_toast(toast)

        self.win.update_games([game_id])

        if self.win.stack.get_visible_child() == self.win.overview:
            self.win.show_overview(None, self.win.active_game_id)

    def on_hide_game_action(self, _widget, _callback=None, game_id=None):
        if not game_id:
            game_id = self.win.active_game_id

        if self.win.stack.get_visible_child() == self.win.overview:
            self.win.on_go_back_action(None, None)
        self.win.games[game_id].toggle_hidden()
        self.win.update_games([game_id])

        title = self.win.games[game_id].name
        if self.win.games[game_id].hidden:
            # The variable is the title of the game
            toast = Adw.Toast.new(_("{} hidden").format(title))
        else:
            # The variable is the title of the game
            toast = Adw.Toast.new(_("{} unhidden").format(title))
        toast.set_button_label(_("Undo"))
        toast.connect("button-clicked", self.win.on_undo_action, game_id, "hide")
        toast.set_priority(Adw.ToastPriority.HIGH)
        if (game_id, "hide") in self.win.toasts.keys():
            # Dismiss the toast if there already is one
            self.win.toasts[(game_id, "hide")].dismiss()
        self.win.toasts[(game_id, "hide")] = toast
        self.win.toast_overlay.add_toast(toast)

    def on_edit_details_action(self, _widget, _callback=None):
        create_details_window(self.win, self.win.active_game_id)

    def on_add_game_action(self, _widget, _callback=None):
        create_details_window(self.win)

    def on_import_action(self, _widget, _callback=None):
        self.win.importer = Importer(self.win)

        self.win.importer.blocker = True

        if self.win.schema.get_boolean("steam"):
            steam_parser(self.win)

        if self.win.schema.get_boolean("lutris"):
            lutris_parser(self.win)

        if self.win.schema.get_boolean("heroic"):
            heroic_parser(self.win)

        if self.win.schema.get_boolean("bottles"):
            bottles_parser(self.win)

        self.win.importer.blocker = False

        if self.win.importer.import_dialog.is_visible and self.win.importer.queue == 0:
            self.win.importer.queue = 1
            self.win.importer.save_game()

    def on_remove_game_action(self, _widget, _callback=None):
        # Add "removed=True" to the game properties so it can be deleted on next init
        game_id = self.win.active_game_id

        data = get_games(self.win, [game_id])[game_id]
        data["removed"] = True
        save_game(self.win, data)

        self.win.update_games([game_id])
        if self.win.stack.get_visible_child() == self.win.overview:
            self.win.on_go_back_action(None, None)

        title = self.win.games[game_id].name
        # The variable is the title of the game
        toast = Adw.Toast.new(_("{} removed").format(title))
        toast.set_button_label(_("Undo"))
        toast.connect("button-clicked", self.win.on_undo_action, game_id, "remove")
        toast.set_priority(Adw.ToastPriority.HIGH)
        self.win.toasts[(game_id, "remove")] = toast
        self.win.toast_overlay.add_toast(toast)

    def on_quit_action(self, _widget, _callback=None):
        self.quit()

    def create_action(self, name, callback, shortcuts=None, win=None):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        if not win:
            self.add_action(action)
            if shortcuts:
                self.set_accels_for_action(f"app.{name}", shortcuts)
        else:
            win.add_action(action)
            if shortcuts:
                self.set_accels_for_action(f"win.{name}", shortcuts)


def main(version):  # pylint: disable=unused-argument
    app = CartridgesApplication()
    return app.run(sys.argv)
