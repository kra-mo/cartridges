# steam_parser.py
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

import os
import re
import time

from gi.repository import GLib, Gtk
from steam.utils.appcache import parse_appinfo

from .create_dialog import create_dialog
from .save_cover import save_cover


def steam_parser(parent_widget, action):
    schema = parent_widget.schema
    steam_dir = os.path.expanduser(schema.get_string("steam-location"))

    def steam_not_found():
        if os.path.exists(
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/")
        ):
            schema.set_string(
                "steam-location", "~/.var/app/com.valvesoftware.Steam/data/Steam/"
            )
            action(None, None)
        elif os.path.exists(os.path.expanduser("~/.steam/steam/")):
            schema.set_string("steam-location", "~/.steam/steam/")
            action(None, None)
        else:
            filechooser = Gtk.FileDialog.new()

            def set_steam_dir(_source, result, _unused):
                try:
                    schema.set_string(
                        "steam-location",
                        filechooser.select_folder_finish(result).get_path(),
                    )
                    action(None, None)
                except GLib.GError:
                    return

            def choose_folder(_widget):
                filechooser.select_folder(parent_widget, None, set_steam_dir, None)

            def response(widget, response):
                if response == "choose_folder":
                    choose_folder(widget)

            create_dialog(
                parent_widget,
                _("Couldn't Import Games"),
                _("The Steam directory cannot be found."),
                "choose_folder",
                _("Set Steam Location"),
            ).connect("response", response)

    if os.path.exists(os.path.join(steam_dir, "steamapps")):
        pass
    elif os.path.exists(os.path.join(steam_dir, "steam", "steamapps")):
        schema.set_string("steam-location", os.path.join(steam_dir, "steam"))
    elif os.path.exists(os.path.join(steam_dir, "Steam", "steamapps")):
        schema.set_string("steam-location", os.path.join(steam_dir, "Steam"))
    else:
        steam_not_found()
        return {}

    steam_dir = os.path.expanduser(schema.get_string("steam-location"))

    appmanifests = []
    datatypes = ["appid", "name"]
    steam_games = {}
    current_time = int(time.time())

    for open_file in os.listdir(os.path.join(steam_dir, "steamapps")):
        path = os.path.join(steam_dir, "steamapps", open_file)
        if os.path.isfile(path) and "appmanifest" in open_file:
            appmanifests.append(path)

    with open("/home/kramo/.steam/steam/appcache/appinfo.vdf", "rb") as open_file:
        _header, apps = parse_appinfo(open_file)

        developers = {
            app["appid"]: app["data"]["appinfo"]["common"]["associations"]["0"]["name"]
            for app in apps
            if "common" in app["data"]["appinfo"]
            and "associations" in app["data"]["appinfo"]["common"]
            and "0" in app["data"]["appinfo"]["common"]["associations"]
        }

    for appmanifest in appmanifests:
        values = {}
        with open(appmanifest, "r") as open_file:
            data = open_file.read()
            open_file.close()
        for datatype in datatypes:
            value = re.findall('"' + datatype + '"\t\t"(.*)"\n', data)
            values[datatype] = value[0]

        values["game_id"] = "steam_" + values["appid"]

        if (
            values["game_id"] in parent_widget.games
            and not parent_widget.games[values["game_id"]].removed
        ):
            continue

        values["executable"] = "xdg-open steam://rungameid/" + values["appid"]
        values["hidden"] = False
        values["source"] = "steam"
        values["added"] = current_time
        values["last_played"] = 0
        try:
            values["developer"] = developers[int(values["appid"])]
        except KeyError:
            pass

        if os.path.isfile(
            os.path.join(
                steam_dir,
                "appcache",
                "librarycache",
                values["appid"] + "_library_600x900.jpg",
            )
        ):
            save_cover(
                values,
                parent_widget,
                os.path.join(
                    steam_dir,
                    "appcache",
                    "librarycache",
                    values["appid"] + "_library_600x900.jpg",
                ),
            )

        steam_games[values["game_id"]] = values

    if len(steam_games) == 0:
        create_dialog(
            parent_widget,
            _("No Games Found"),
            _("No new games were found in the Steam library."),
        )
    elif len(steam_games) == 1:
        create_dialog(
            parent_widget, _("Steam Games Imported"), _("Successfully imported 1 game.")
        )
    elif len(steam_games) > 1:
        create_dialog(
            parent_widget,
            _("Steam Games Imported"),
            _("Successfully imported")
            + " "
            + str(len(steam_games))
            + " "
            + _("games."),
        )
    return steam_games
