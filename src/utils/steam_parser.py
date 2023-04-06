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
import urllib.request
from pathlib import Path
from time import time

from gi.repository import Gio


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


def get_game(task, datatypes, current_time, parent_widget, appmanifest, steam_dir):
    values = {}

    data = appmanifest.read_text("utf-8")
    for datatype in datatypes:
        value = re.findall(f'"{datatype}"\t\t"(.*)"\n', data, re.IGNORECASE)
        try:
            values[datatype] = value[0]
        except IndexError:
            task.return_value((None, None))
            return

    values["game_id"] = f'steam_{values["appid"]}'

    if (
        values["game_id"] in parent_widget.games
        and not parent_widget.games[values["game_id"]].removed
    ):
        task.return_value((None, None))
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

    image_path = (
        steam_dir
        / "appcache"
        / "librarycache"
        / f'{values["appid"]}_library_600x900.jpg'
    )

    try:
        with urllib.request.urlopen(
            f'https://store.steampowered.com/api/appdetails?appids={values["appid"]}',
            timeout=5,
        ) as open_file:
            content = open_file.read().decode("utf-8")
    except urllib.error.URLError:
        task.return_value((values, image_path if image_path.exists() else None))
        return

    values = update_values_from_data(content, values)
    task.return_value((values, image_path if image_path.exists() else None))


def get_games_async(parent_widget, appmanifests, steam_dir, importer):
    datatypes = ["appid", "name"]
    current_time = int(time())

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
            )

        return wrapper

    def update_games(_task, result):
        final_values = result.propagate_value()[1]
        # No need for an if statement as final_value would be None for games we don't want to save
        importer.save_game(final_values[0], final_values[1])

    for appmanifest in appmanifests:
        task = Gio.Task.new(None, None, update_games)
        task.run_in_thread(
            create_func(datatypes, current_time, parent_widget, appmanifest, steam_dir)
        )


def steam_parser(parent_widget):
    schema = parent_widget.schema
    steam_dir = Path(schema.get_string("steam-location")).expanduser()

    def steam_not_found():
        if Path("~/.var/app/com.valvesoftware.Steam/data/Steam/").expanduser().exists():
            schema.set_string(
                "steam-location", "~/.var/app/com.valvesoftware.Steam/data/Steam/"
            )
        elif Path("~/.steam/steam/").expanduser().exists():
            schema.set_string("steam-location", "~/.steam/steam/")
        elif (
            os.name == "nt"
            and (Path(os.getenv("programfiles(x86)")) / "Steam").exists()
        ):
            schema.set_string(
                "steam-location", str(Path(os.getenv("programfiles(x86)")) / "Steam")
            )

    if (steam_dir / "steamapps").exists():
        pass
    elif (steam_dir / "steam" / "steamapps").exists():
        schema.set_string("steam-location", str(steam_dir / "steam"))
    elif (steam_dir / "Steam" / "steamapps").exists():
        schema.set_string("steam-location", str(steam_dir / "Steam"))
    else:
        steam_not_found()
        steam_parser(parent_widget)
        return

    steam_dir = Path(schema.get_string("steam-location")).expanduser()
    appmanifests = []

    steam_dirs = [Path(directory) for directory in schema.get_strv("steam-extra-dirs")]
    steam_dirs.append(steam_dir)

    for directory in steam_dirs:
        if not (directory / "steamapps").exists():
            steam_dirs.remove(directory)

    for directory in steam_dirs:
        for open_file in (directory / "steamapps").iterdir():
            if open_file.is_file() and "appmanifest" in open_file.name:
                appmanifests.append(open_file)

    importer = parent_widget.importer
    importer.total_queue += len(appmanifests)
    importer.queue += len(appmanifests)

    get_games_async(parent_widget, appmanifests, directory, importer)
