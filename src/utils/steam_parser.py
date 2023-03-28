# steam_parser.py
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
import os
import re
import time
import urllib.request

from gi.repository import Gio, GLib


def update_values_from_data(content, values):
    basic_data = json.loads(content)[values["appid"]]
    if not basic_data["success"]:
        values["blacklisted"] = True
    else:
        data = basic_data["data"]
        values["developer"] = ", ".join(data["developers"])

        if data["type"] != "game":
            values["blacklisted"] = True

    return values


def get_game(
    task, datatypes, current_time, parent_widget, appmanifest, steam_dir, importer
):
    values = {}

    with open(appmanifest, "r") as open_file:
        data = open_file.read()
    for datatype in datatypes:
        value = re.findall(f'"{datatype}"\t\t"(.*)"\n', data)
        values[datatype] = value[0]

    values["game_id"] = f'steam_{values["appid"]}'

    if (
        values["game_id"] in parent_widget.games
        and not parent_widget.games[values["game_id"]].removed
    ):
        task.return_value(None)
        return

    values["executable"] = (
        ["start", f'steam://rungameid/{values["appid"]}']
        if os.name == "nt"
        else ["xdg-open", f'steam://rungameid/{values["appid"]}']
    )
    values["hidden"] = False
    values["source"] = "steam"
    values["added"] = current_time
    values["last_played"] = 0

    url = f'https://store.steampowered.com/api/appdetails?appids={values["appid"]}'

    # On Linux the request is made through gvfs so the app can run without network permissions
    if os.name == "nt":
        try:
            with urllib.request.urlopen(url, timeout=10) as open_file:
                content = open_file.read().decode("utf-8")
        except urllib.error.URLError:
            content = None
    else:
        open_file = Gio.File.new_for_uri(url)
        try:
            content = open_file.load_contents()[1]
        except GLib.GError:
            content = None

    if content:
        values = update_values_from_data(content, values)

    if os.path.isfile(
        os.path.join(
            steam_dir,
            "appcache",
            "librarycache",
            f'{values["appid"]}_library_600x900.jpg',
        )
    ):
        importer.save_cover(
            values["game_id"],
            os.path.join(
                steam_dir,
                "appcache",
                "librarycache",
                f'{values["appid"]}_library_600x900.jpg',
            ),
        )

    task.return_value(values)
    return


def get_games_async(parent_widget, appmanifests, steam_dir, importer):
    datatypes = ["appid", "name"]
    current_time = int(time.time())

    # Wrap the function in another one as Gio.Task.run_in_thread does not allow for passing args
    def create_func(datatypes, current_time, parent_widget, appmanifest, steam_dir):
        def wrapper(task, *_unused):
            get_game(
                task,
                datatypes,
                current_time,
                parent_widget,
                appmanifest,
                steam_dir,
                importer,
            )

        return wrapper

    def update_games(_task, result):
        try:
            final_values = result.propagate_value()[1]
            # No need for an if statement as final_value would be None for games we don't want to save
            importer.save_game(final_values)
        except GLib.GError:  # Handle the exception for the timeout
            importer.save_game()

    for appmanifest in appmanifests:
        cancellable = Gio.Cancellable.new()
        GLib.timeout_add_seconds(5, cancellable.cancel)

        task = Gio.Task.new(None, cancellable, update_games)
        task.set_return_on_cancel(True)
        task.run_in_thread(
            create_func(datatypes, current_time, parent_widget, appmanifest, steam_dir)
        )


def steam_parser(parent_widget):
    schema = parent_widget.schema
    steam_dir = os.path.expanduser(schema.get_string("steam-location"))

    def steam_not_found():
        if os.path.exists(
            os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/")
        ):
            schema.set_string(
                "steam-location", "~/.var/app/com.valvesoftware.Steam/data/Steam/"
            )
        elif os.path.exists(os.path.expanduser("~/.steam/steam/")):
            schema.set_string("steam-location", "~/.steam/steam/")
        elif os.path.exists(os.path.join(os.getenv("programfiles(x86)"), "Steam")):
            schema.set_string(
                "steam-location", os.path.join(os.getenv("programfiles(x86)"), "Steam")
            )
        else:
            return

    if os.path.exists(os.path.join(steam_dir, "steamapps")):
        pass
    elif os.path.exists(os.path.join(steam_dir, "steam", "steamapps")):
        schema.set_string("steam-location", os.path.join(steam_dir, "steam"))
    elif os.path.exists(os.path.join(steam_dir, "Steam", "steamapps")):
        schema.set_string("steam-location", os.path.join(steam_dir, "Steam"))
    else:
        steam_not_found()
        return

    steam_dir = os.path.expanduser(schema.get_string("steam-location"))
    appmanifests = []

    steam_dirs = schema.get_strv("steam-extra-dirs")
    steam_dirs.append(steam_dir)

    for directory in steam_dirs:
        if not os.path.exists(os.path.join(directory, "steamapps")):
            steam_dirs.remove(directory)

    for directory in steam_dirs:
        for open_file in os.listdir(os.path.join(directory, "steamapps")):
            path = os.path.join(directory, "steamapps", open_file)
            if os.path.isfile(path) and "appmanifest" in open_file:
                appmanifests.append(path)

    importer = parent_widget.importer
    importer.total_queue += len(appmanifests)
    importer.queue += len(appmanifests)

    get_games_async(parent_widget, appmanifests, directory, importer)
