# main.py
#
# Copyright 2022 kramo
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

import gi, sys, os, time, json

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Gio, GLib, Adw

from .window import CartridgesWindow
from .preferences import PreferencesWindow
from .toggle_hidden import toggle_hidden
from .save_games import save_games
from .run_command import run_command
from .steam_parser import steam_parser
from .heroic_parser import heroic_parser
from .bottles_parser import bottles_parser
from .create_details_window import create_details_window

class CartridgesApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="hu.kramo.Cartridges", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action("quit", self.on_quit_action, ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action, ["<primary>comma"])
        self.create_action("steam_import", self.on_steam_import_action)
        self.create_action("heroic_import", self.on_heroic_import_action)
        self.create_action("bottles_import", self.on_bottles_import_action)
        self.create_action("launch_game", self.on_launch_game_action)
        self.create_action("hide_game", self.on_hide_game_action)
        self.create_action("edit_details", self.on_edit_details_action)
        self.create_action("add_game", self.on_add_game_action, ["<primary>n"])
        self.create_action("remove_game", self.on_remove_game_action)

    def do_activate(self):

        # Create the main window
        self.win = self.props.active_window
        if not self.win:
            self.win = CartridgesWindow(application=self)

        # Save window geometry
        state_settings = Gio.Settings(schema_id="hu.kramo.Cartridge.State")
        state_settings.bind("width", self.win, "default-width", Gio.SettingsBindFlags.DEFAULT)
        state_settings.bind("height", self.win, "default-height", Gio.SettingsBindFlags.DEFAULT)
        state_settings.bind("is-maximized", self.win, "maximized", Gio.SettingsBindFlags.DEFAULT)

        self.win.present()

        # Create actions for the main window
        self.create_action("show_hidden", self.win.on_show_hidden_action, ["<primary>h"], self.win)
        self.create_action("go_back", self.win.on_go_back_action, ["<alt>Left"], self.win)
        self.create_action("go_to_parent", self.win.on_go_to_parent_action, ["<alt>Up"], self.win)
        self.create_action("toggle_search", self.win.on_toggle_search_action, ["<primary>f"], self.win)
        self.create_action("escape", self.win.on_escape_action, ["Escape"], self.win)
        self.create_action("undo_remove", self.win.on_undo_remove_action, ["<primary>z"], self.win)
        self.create_action("open_menu", self.win.on_open_menu_action, ["F10"], self.win)
        self.win.sort = Gio.SimpleAction.new_stateful("sort_by", GLib.VariantType.new("s"), GLib.Variant("s", "a-z"))
        self.win.add_action(self.win.sort)
        self.win.sort.connect("activate", self.win.on_sort_action)
        self.win.on_sort_action(self.win.sort, state_settings.get_value("sort-mode"))

    def on_about_action(self, widget, callback=None):
        about = Adw.AboutWindow(transient_for=self.win,
                                application_name=_("Cartridges"),
                                application_icon="hu.kramo.Cartridges",
                                developer_name="kramo",
                                version="0.1.2",
                                developers=["kramo https://kramo.hu", "Paweł Lidwin https://github.com/imLinguin"],
                                designers=["kramo https://kramo.hu"],
                                copyright="© 2022 kramo",
                                license_type=Gtk.License.GPL_3_0,
                                issue_url="https://github.com/kra-mo/cartridges/issues/new",
                                website="https://github.com/kra-mo/cartridges",
                                # Translators: Replace this with your name for it to show up in the about window.
                                translator_credits=_("translator_credits"))
        about.present()

    def on_preferences_action(self, widget, callback=None):
        PreferencesWindow(self.win).present()

    def on_steam_import_action(self, widget, callback=None):
        games = steam_parser(self.win, self.on_steam_import_action)
        save_games(games)
        self.win.update_games(games.keys())

    def on_heroic_import_action(self, widget, callback=None):
        games = heroic_parser(self.win, self.on_heroic_import_action)
        save_games(games)
        self.win.update_games(games.keys())

    def on_bottles_import_action(self, widget, callback=None):
        games = bottles_parser(self.win, self.on_bottles_import_action)
        save_games(games)
        self.win.update_games(games.keys())

    def on_launch_game_action(self, widget, callback=None):

        # Launch the game and update the last played value
        self.win.games[self.win.active_game_id]["last_played"] = int(time.time())
        save_games({self.win.active_game_id : self.win.games[self.win.active_game_id]})
        self.win.update_games([self.win.active_game_id])
        run_command(self.win, self.win.games[self.win.active_game_id]["executable"])

        if self.win.stack.get_visible_child() == self.win.overview:
            self.win.show_overview(None, self.win.active_game_id)

    def on_hide_game_action(self, widget, callback=None):
        if self.win.stack.get_visible_child() == self.win.overview:
            self.win.on_go_back_action(None, None)
        toggle_hidden(self.win.active_game_id)
        self.win.update_games([self.win.active_game_id])

    def on_edit_details_action(self, widget, callback=None):
        create_details_window(self.win, self.win.active_game_id)

    def on_add_game_action(self, widget, callback=None):
        create_details_window(self.win)

    def on_remove_game_action(self, widget, callback=None):

        # Add "removed=True" to the game properties so it can be deleted on next init
        game_id = self.win.active_game_id
        open_file = open(os.path.join(os.path.join(os.environ.get("XDG_DATA_HOME"), "cartridges", "games", game_id + ".json")), "r")
        data = json.loads(open_file.read())
        open_file.close()
        data["removed"] = True
        save_games({game_id : data})

        self.win.update_games([game_id])
        if self.win.stack.get_visible_child() == self.win.overview:
            self.win.on_go_back_action(None, None)

        # Create toast for undoing the remove action
        toast = Adw.Toast.new(self.win.games[game_id]["name"] + " " + (_("removed")))
        toast.set_button_label(_("Undo"))
        toast.connect("button-clicked", self.win.on_undo_remove_action, game_id)
        toast.set_priority(Adw.ToastPriority.HIGH)
        self.win.toasts[game_id] = toast
        self.win.toast_overlay.add_toast(toast)

    def on_quit_action(self, widget, callback=None):
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

def main(version):
    app = CartridgesApplication()
    return app.run(sys.argv)

