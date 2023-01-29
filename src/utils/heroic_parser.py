# heroic_parser.py
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

def heroic_parser(parent_widget, action):
    import os, json, time

    from gi.repository import Gtk, GLib

    from .create_dialog import create_dialog
    from .save_cover import save_cover

    schema = parent_widget.schema
    heroic_dir = os.path.expanduser(os.path.join(schema.get_string("heroic-location")))

    def heroic_not_found():
        filechooser = Gtk.FileDialog.new()

        def set_heroic_dir(source, result, _):
            try:
                schema.set_string("heroic-location", filechooser.select_folder_finish(result).get_path())
                heroic_dir = heroic_dir = os.path.join(schema.get_string("heroic-location"))
                action(None, None)
            except GLib.GError:
                return

        def choose_folder(widget):
            filechooser.select_folder(parent_widget, None, set_heroic_dir, None)

        def response(widget, response):
            if response == "choose_folder":
                choose_folder(widget)

        create_dialog(parent_widget, _("Couldn't Import Games"), _("Heroic directory cannot be found."), "choose_folder", _("Set Heroic Location")).connect("response", response)

    if os.path.exists(os.path.join(heroic_dir, "config.json")) == True:
        pass
    else:
        heroic_not_found()
        return {}

    heroic_games = {}
    current_time = int(time.time())

    # Import Epic games
    if schema.get_boolean("heroic-import-epic") == False:
        pass
    elif os.path.exists(os.path.join(heroic_dir, "lib-cache", "installInfo.json")) == True:
        open_file = open(os.path.join(heroic_dir, "lib-cache", "installInfo.json"), "r")
        data = open_file.read()
        open_file.close()
        installInfo = json.loads(data)
        for item in installInfo:
            if installInfo[item]["install"] != None:
                values = {}
                app_name = installInfo[item]["game"]["app_name"]

                values["game_id"] = "heroic_epic_" + app_name

                if values["game_id"] in parent_widget.games and "removed" not in parent_widget.games[values["game_id"]].keys():
                    continue

                values["name"] = installInfo[item]["game"]["title"]
                values["executable"] = "xdg-open heroic://launch/" + app_name
                values["hidden"] = False
                values["source"] = "heroic_epic"
                values["added"] = current_time
                values["last_played"] = 0
                if os.path.isfile(os.path.join(heroic_dir, "icons", app_name + ".jpg")) == True:
                    values["pixbuf_options"] = save_cover(values, parent_widget, os.path.join(os.path.join(heroic_dir, "icons", app_name + ".jpg")))

                heroic_games[values["game_id"]] = values

    # Import GOG games
    if schema.get_boolean("heroic-import-gog") == False:
        pass
    elif os.path.exists(os.path.join(heroic_dir, "gog_store", "installed.json")) == True:
        open_file = open(os.path.join(heroic_dir, "gog_store", "installed.json"), "r")
        data = open_file.read()
        open_file.close()
        installed = json.loads(data)
        for item in installed["installed"]:
            values = {}
            app_name = item["appName"]

            values["game_id"] = "heroic_gog_" + app_name

            if values["game_id"] in parent_widget.games and "removed" not in parent_widget.games[values["game_id"]].keys():
                    continue

            # Get game title from library.json as it's not present in installed.json
            open_file = open(os.path.join(heroic_dir, "gog_store", "library.json"), "r")
            data = open_file.read()
            open_file.close()
            library = json.loads(data)
            for game in library["games"]:
                if game["app_name"] == app_name:
                    values["name"] = game["title"]
                    break

            values["executable"] = "xdg-open heroic://launch/" + app_name
            values["hidden"] = False
            values["source"] = "heroic_gog"
            values["added"] = current_time
            values["last_played"] = 0
            if os.path.isfile(os.path.join(heroic_dir, "icons", app_name + ".jpg")) == True:
                    values["pixbuf_options"] = save_cover(values, parent_widget, os.path.join(os.path.join(heroic_dir, "icons", app_name + ".jpg")))
            heroic_games[values["game_id"]] = values

    # Import sideloaded games
    if schema.get_boolean("heroic-import-sideload") == False:
        pass
    elif os.path.exists(os.path.join(heroic_dir, "sideload_apps", "library.json")) == True:
        open_file = open(os.path.join(heroic_dir, "sideload_apps", "library.json"), "r")
        data = open_file.read()
        open_file.close()
        library = json.loads(data)
        for item in library["games"]:
            values = {}
            app_name = item["app_name"]

            values["game_id"] = "heroic_sideload_" + app_name

            if values["game_id"] in parent_widget.games and "removed" not in parent_widget.games[values["game_id"]].keys():
                continue

            values["name"] = item["title"]
            values["executable"] = "xdg-open heroic://launch/" + app_name
            values["hidden"] = False
            values["source"] = "heroic_sideload"
            values["added"] = current_time
            values["last_played"] = 0
            if os.path.isfile(os.path.join(heroic_dir, "icons", app_name + ".jpg")) == True:
                values["pixbuf_options"] = save_cover(values, parent_widget, os.path.join(os.path.join(heroic_dir, "icons", app_name + ".jpg")))
            heroic_games[values["game_id"]] = values

    if len(heroic_games) == 0:
        create_dialog(parent_widget, _("No Games Found"), _("No new games found in Heroic library."))
    elif len(heroic_games) == 1:
        create_dialog(parent_widget, _("Heroic Games Imported"), _("Successfully imported 1 game."))
    elif len(heroic_games) > 1:
        create_dialog(parent_widget, _("Heroic Games Imported"), _("Successfully imported") + " " + str(len(heroic_games)) + " " + _("games."))
    return heroic_games
