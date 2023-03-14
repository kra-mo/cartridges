# bottles_parser.py
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

def bottles_parser(parent_widget, action):
    import os, yaml, time

    from gi.repository import Gtk, GLib

    from .create_dialog import create_dialog
    from .save_cover import save_cover

    schema = parent_widget.schema
    bottles_dir = os.path.expanduser(schema.get_string("bottles-location"))

    def bottles_not_found():
        if os.path.exists(os.path.expanduser("~/.var/app/com.usebottles.bottles/data/bottles/")):
            schema.set_string("bottles-location", "~/.var/app/com.usebottles.bottles/data/bottles/")
            action(None, None)
        elif os.path.exists(os.path.join(os.environ.get("XDG_DATA_HOME"), "bottles")):
            schema.set_string("bottles-location", os.path.join(os.environ.get("XDG_DATA_HOME"), "bottles"))
            action(None, None)
        else:
            filechooser = Gtk.FileDialog.new()

            def set_bottles_dir(source, result, _):
                try:
                    schema.set_string("bottles-location", filechooser.select_folder_finish(result).get_path())
                    action(None, None)
                except GLib.GError:
                    return

            def choose_folder(widget):
                filechooser.select_folder(parent_widget, None, set_bottles_dir, None)

            def response(widget, response):
                if response == "choose_folder":
                    choose_folder(widget)

            create_dialog(parent_widget, _("Couldn't Import Games"), _("The Bottles directory cannot be found."), "choose_folder", _("Set Bottles Location")).connect("response", response)

    if os.path.isfile(os.path.join(bottles_dir, "library.yml")):
        pass
    else:
        bottles_not_found()
        return {}

    bottles_dir = os.path.expanduser(schema.get_string("bottles-location"))

    datatypes = ["path", "id", "name", "thumbnail"]
    bottles_games = {}
    current_time = int(time.time())

    open_file = open(os.path.join(bottles_dir, "library.yml"), "r")
    data = open_file.read()
    open_file.close()

    library = yaml.load(data, Loader=yaml.Loader)

    for game in library:
        game = library[game]
        values = {}

        values["game_id"] = "bottles_" + game["id"]

        if values["game_id"] in parent_widget.games and "removed" not in parent_widget.games[
            values["game_id"]].keys():
            continue

        values["name"] = game["name"]
        values["executable"] = "xdg-open bottles:run/" + game["bottle"]["name"] + "/" + game["name"]
        values["hidden"] = False
        values["source"] = "bottles"
        values["added"] = current_time
        values["last_played"] = 0

        if game["thumbnail"]:
            values["pixbuf_options"] = save_cover(values, parent_widget, os.path.join(bottles_dir, "bottles", game["bottle"]["path"], "grids", game["thumbnail"].split(":")[1]))

        bottles_games[values["game_id"]] = values

    if len(bottles_games) == 0:
        create_dialog(parent_widget, _("No Games Found"), _("No new games were found in the Bottles library."))
    elif len(bottles_games) == 1:
        create_dialog(parent_widget, _("Bottles Games Imported"), _("Successfully imported 1 game."))
    elif len(bottles_games) > 1:
        create_dialog(parent_widget, _("Bottles Games Imported"), _("Successfully imported") + " " + str(len(bottles_games)) + " " + _("games."))
    return bottles_games
