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

from .window import GameShelfWindow
from .preferences import PreferencesWindow
from .toggle_hidden import toggle_hidden
from .save_games import save_games
from .run_command import run_command
from .steam_parser import steam_parser
from .heroic_parser import heroic_parser
from .create_details_window import create_details_window

class GameShelfApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id="hu.kramo.GameShelf", flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.create_action("quit", self.on_quit_action, ["<primary>q"])
        self.create_action("about", self.on_about_action)
        self.create_action("preferences", self.on_preferences_action)
        self.create_action("steam_import", self.on_steam_import_action)
        self.create_action("heroic_import", self.on_heroic_import_action)
        self.create_action("launch_game", self.on_launch_game_action)
        self.create_action("hide_game", self.on_hide_game_action)
        self.create_action("edit_details", self.on_edit_details_action)
        self.create_action("add_game", self.on_add_game_action)
        self.create_action("remove_game", self.on_remove_game_action)

    def do_activate(self):

        # Create the main window
        win = self.props.active_window
        if not win:
            win = GameShelfWindow(application=self)

        win.present()

        # Create actions for the main window
        self.create_action("show_hidden", win.on_show_hidden_action, None, win)
        self.create_action("go_back", win.on_go_back_action, ["<alt>Left"], win)
        self.create_action("go_to_parent", win.on_go_to_parent_action, ["<alt>Up"], win)
        self.create_action("toggle_search", win.on_toggle_search_action, ["<primary>f"], win)
        self.create_action("escape", win.on_escape_action, ["Escape"], win)
        self.create_action("undo_remove", win.on_undo_remove_action, ["<primary>z"], win)
        win.sort = Gio.SimpleAction.new_stateful("sort_by", GLib.VariantType.new("s"), GLib.Variant("s", "a-z"))
        win.add_action(win.sort)
        win.sort.connect("activate", win.on_sort_action)
        win.on_sort_action(win.sort, win.schema.get_value("sort-mode"))

    def on_about_action(self, widget, callback=None):
        about = Adw.AboutWindow(transient_for=self.props.active_window,
                                application_name="Game Shelf",
                                application_icon="hu.kramo.GameShelf",
                                developer_name="kramo",
                                version="0.1.1",
                                developers=["kramo"],
                                copyright="© 2022 kramo",
                                license_type=Gtk.License.GPL_3_0)
        about.present()

    def on_preferences_action(self, widget, callback=None):
        PreferencesWindow(self.props.active_window).present()

    def on_steam_import_action(self, widget, callback=None):
        games = steam_parser(self.props.active_window, self.on_steam_import_action)
        save_games(games)
        self.props.active_window.update_games(games.keys())

    def on_heroic_import_action(self, widget, callback=None):
        games = heroic_parser(self.props.active_window, self.on_heroic_import_action)
        save_games(games)
        self.props.active_window.update_games(games.keys())

    def on_launch_game_action(self, widget, callback=None):

        # Launch the game and update the last played value
        self.props.active_window.games[self.props.active_window.active_game_id]["last_played"] = int(time.time())
        save_games({self.props.active_window.active_game_id : self.props.active_window.games[self.props.active_window.active_game_id]})
        self.props.active_window.update_games([self.props.active_window.active_game_id])
        run_command(self.props.active_window, self.props.active_window.games[self.props.active_window.active_game_id]["executable"])

        if self.props.active_window.stack.get_visible_child() == self.props.active_window.overview:
            self.props.active_window.show_overview(None, self.props.active_window.active_game_id)

    def on_hide_game_action(self, widget, callback=None):
        if self.props.active_window.stack.get_visible_child() == self.props.active_window.overview:
            self.props.active_window.on_go_back_action(None, None)
        toggle_hidden(self.props.active_window.active_game_id)
        self.props.active_window.update_games([self.props.active_window.active_game_id])

    def on_edit_details_action(self, widget, callback=None):
        create_details_window(self.props.active_window, self.props.active_window.active_game_id)

    def on_add_game_action(self, widget, callback=None):
        create_details_window(self.props.active_window)

    def on_remove_game_action(self, widget, callback=None):

        # Add "removed=True" to the game properties so it can be deleted on next init
        game_id = self.props.active_window.active_game_id
        open_file = open(os.path.join(os.path.join(os.environ.get("XDG_DATA_HOME"), "games", game_id + ".json")), "r")
        data = json.loads(open_file.read())
        open_file.close()
        data["removed"] = True
        save_games({game_id : data})

        self.props.active_window.update_games([game_id])
        if self.props.active_window.stack.get_visible_child() == self.props.active_window.overview:
            self.props.active_window.on_go_back_action(None, None)

        # Create toast for undoing the remove action
        toast = Adw.Toast.new(self.props.active_window.games[game_id]["name"] + " " + (_("removed")))
        toast.set_button_label(_("Undo"))
        toast.connect("button-clicked", self.props.active_window.on_undo_remove_action, game_id)
        toast.set_priority(Adw.ToastPriority.HIGH)
        self.props.active_window.toasts[game_id] = toast
        self.props.active_window.toast_overlay.add_toast(toast)

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
    app = GameShelfApplication()
    return app.run(sys.argv)

