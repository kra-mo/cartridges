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

from gi.repository import Adw, Gio, GLib, Gtk

from .create_dialog import create_dialog
from .save_cover import save_cover
from .save_games import save_games


def upadte_values_from_data(content, values):
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

    with open(appmanifest, "r") as open_file:
        data = open_file.read()
        open_file.close()
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
        f'start steam://rungameid/{values["appid"]}'
        if os.name == "nt"
        else f'xdg-open steam://rungameid/{values["appid"]}'
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
        values = upadte_values_from_data(content, values)

    if os.path.isfile(
        os.path.join(
            steam_dir,
            "appcache",
            "librarycache",
            f'{values["appid"]}_library_600x900.jpg',
        )
    ):
        save_cover(
            values,
            parent_widget,
            os.path.join(
                steam_dir,
                "appcache",
                "librarycache",
                f'{values["appid"]}_library_600x900.jpg',
            ),
        )

    task.return_value(values)
    return


def get_games_async(parent_widget, appmanifests, steam_dir, import_dialog, progressbar):
    datatypes = ["appid", "name"]
    current_time = int(time.time())

    steam_games = {}
    queue = 0

    # Wrap the function in another one as Gio.Task.run_in_thread does not allow for passing args
    def create_func(datatypes, current_time, parent_widget, appmanifest, steam_dir):
        def wrapper(task, *_unused):
            get_game(
                task, datatypes, current_time, parent_widget, appmanifest, steam_dir
            )

        return wrapper

    def update_games(_task, result, parent_widget):
        nonlocal queue
        nonlocal total_queue
        nonlocal import_dialog
        nonlocal progressbar

        queue -= 1
        progressbar.set_fraction(1 - (queue / total_queue))

        try:
            final_values = result.propagate_value()[1]
            steam_games[final_values["game_id"]] = final_values
        except (TypeError, GLib.GError):
            pass

        if queue == 0:
            save_games(steam_games)
            parent_widget.update_games(steam_games)
            import_dialog.close()
            games_no = len(
                {
                    game_id: final_values
                    for game_id, final_values in steam_games.items()
                    if "blacklisted" not in final_values.keys()
                }
            )

            if games_no == 0:
                create_dialog(
                    parent_widget,
                    _("No Games Found"),
                    _("No new games were found in the Steam library."),
                )
            elif games_no == 1:
                create_dialog(
                    parent_widget,
                    _("Steam Games Imported"),
                    _("Successfully imported 1 game."),
                )
            elif games_no > 1:
                games_no = str(games_no)
                create_dialog(
                    parent_widget,
                    _("Steam Games Imported"),
                    # The variable is the number of games
                    _(f"Successfully imported {games_no} games."),
                )

    total_queue = 0
    for appmanifest in appmanifests:
        queue += 1
        total_queue += 1

        cancellable = Gio.Cancellable.new()
        GLib.timeout_add_seconds(5, cancellable.cancel)

        task = Gio.Task.new(None, cancellable, update_games, parent_widget)
        task.set_return_on_cancel(True)
        task.run_in_thread(
            create_func(datatypes, current_time, parent_widget, appmanifest, steam_dir)
        )


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
        elif os.path.exists(os.path.join(os.getenv("programfiles(x86)"), "Steam")):
            schema.set_string(
                "steam-location", os.path.join(os.getenv("programfiles(x86)"), "Steam")
            )
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

    progressbar = Gtk.ProgressBar(margin_start=12, margin_end=12)
    import_statuspage = Adw.StatusPage(
        title=_("Importing Games…"),
        description=_("Talking to Steam"),
        child=progressbar,
    )

    import_dialog = Adw.Window(
        content=import_statuspage,
        modal=True,
        default_width=350,
        default_height=-1,
        transient_for=parent_widget,
        deletable=False,
    )

    import_dialog.present()

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

    get_games_async(parent_widget, appmanifests, directory, import_dialog, progressbar)
