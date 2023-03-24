# heroic_parser.py
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

import hashlib
import json
import os
import time

from gi.repository import GLib, Gtk

from .create_dialog import create_dialog
from .save_cover import save_cover


def heroic_parser(parent_widget, action):
    schema = parent_widget.schema
    heroic_dir = os.path.expanduser(schema.get_string("heroic-location"))

    def heroic_not_found():
        if os.path.exists(
            os.path.expanduser("~/.var/app/com.heroicgameslauncher.hgl/config/heroic/")
        ):
            schema.set_string(
                "heroic-location",
                "~/.var/app/com.heroicgameslauncher.hgl/config/heroic/",
            )
            action(None, None)
        elif os.path.exists(
            os.path.join(
                os.getenv("XDG_CONFIG_HOME")
                or os.path.expanduser(os.path.join("~", ".config")),
                "heroic",
            )
        ):
            schema.set_string(
                "heroic-location",
                os.path.join(
                    os.getenv("XDG_CONFIG_HOME")
                    or os.path.expanduser(os.path.join("~", ".config")),
                    "heroic",
                ),
            )
            action(None, None)
        elif os.path.exists(os.path.join(os.getenv("appdata"), "heroic")):
            schema.set_string(
                "heroic-location", os.path.join(os.getenv("appdata"), "heroic")
            )
            action(None, None)
        else:
            filechooser = Gtk.FileDialog.new()

            def set_heroic_dir(_source, result, _unused):
                try:
                    schema.set_string(
                        "heroic-location",
                        filechooser.select_folder_finish(result).get_path(),
                    )
                    action(None, None)
                except GLib.GError:
                    return

            def choose_folder(_widget):
                filechooser.select_folder(parent_widget, None, set_heroic_dir, None)

            def response(widget, response):
                if response == "choose_folder":
                    choose_folder(widget)

            create_dialog(
                parent_widget,
                _("Couldn't Import Games"),
                _("The Heroic directory cannot be found."),
                "choose_folder",
                _("Set Heroic Location"),
            ).connect("response", response)

    if not os.path.exists(os.path.join(heroic_dir, "config.json")):
        heroic_not_found()
        return {}

    heroic_dir = os.path.expanduser(schema.get_string("heroic-location"))

    heroic_games = {}
    current_time = int(time.time())

    # Import Epic games
    if not schema.get_boolean("heroic-import-epic"):
        pass
    elif os.path.exists(os.path.join(heroic_dir, "lib-cache", "library.json")):
        with open(
            os.path.join(heroic_dir, "lib-cache", "library.json"), "r"
        ) as open_file:
            data = open_file.read()
            open_file.close()
        library = json.loads(data)

        try:
            for game in library["library"]:
                if not game["is_installed"]:
                    continue

                values = {}

                app_name = game["app_name"]
                values["game_id"] = f"heroic_epic_{app_name}"

                if (
                    values["game_id"] in parent_widget.games
                    and not parent_widget.games[values["game_id"]].removed
                ):
                    continue

                values["name"] = game["title"]
                values["developer"] = game["developer"]
                values["executable"] = (
                    f"start heroic://launch/{app_name}"
                    if os.name == "nt"
                    else f"xdg-open heroic://launch/{app_name}"
                )
                values["hidden"] = False
                values["source"] = "heroic_epic"
                values["added"] = current_time
                values["last_played"] = 0

                image_path = os.path.join(
                    heroic_dir,
                    "images-cache",
                    hashlib.sha256(
                        (f'{game["art_square"]}?h=400&resize=1&w=300').encode()
                    ).hexdigest(),
                )
                if os.path.exists(image_path):
                    save_cover(values, parent_widget, image_path)

                heroic_games[values["game_id"]] = values
        except KeyError:
            pass

    # Import GOG games
    if not schema.get_boolean("heroic-import-gog"):
        pass
    elif os.path.exists(os.path.join(heroic_dir, "gog_store", "installed.json")):
        with open(
            os.path.join(heroic_dir, "gog_store", "installed.json"), "r"
        ) as open_file:
            data = open_file.read()
            open_file.close()
        installed = json.loads(data)
        for item in installed["installed"]:
            values = {}
            app_name = item["appName"]

            values["game_id"] = f"heroic_gog_{app_name}"

            if (
                values["game_id"] in parent_widget.games
                and not parent_widget.games[values["game_id"]].removed
            ):
                continue

            # Get game title and developer from library.json as they are not present in installed.json
            with open(
                os.path.join(heroic_dir, "gog_store", "library.json"), "r"
            ) as open_file:
                data = open_file.read()
                open_file.close()
            library = json.loads(data)
            for game in library["games"]:
                if game["app_name"] == app_name:
                    values["developer"] = game["developer"]
                    values["name"] = game["title"]
                    image_path = os.path.join(
                        heroic_dir,
                        "images-cache",
                        hashlib.sha256(game["art_square"].encode()).hexdigest(),
                    )
                    if os.path.exists(image_path):
                        save_cover(values, parent_widget, image_path)
                    break

            values["executable"] = (
                f"start heroic://launch/{app_name}"
                if os.name == "nt"
                else f"xdg-open heroic://launch/{app_name}"
            )
            values["hidden"] = False
            values["source"] = "heroic_gog"
            values["added"] = current_time
            values["last_played"] = 0

            heroic_games[values["game_id"]] = values

    # Import sideloaded games
    if not schema.get_boolean("heroic-import-sideload"):
        pass
    elif os.path.exists(os.path.join(heroic_dir, "sideload_apps", "library.json")):
        with open(
            os.path.join(heroic_dir, "sideload_apps", "library.json"), "r"
        ) as open_file:
            data = open_file.read()
            open_file.close()
        library = json.loads(data)
        for item in library["games"]:
            values = {}
            app_name = item["app_name"]

            values["game_id"] = f"heroic_sideload_{app_name}"

            if (
                values["game_id"] in parent_widget.games
                and not parent_widget.games[values["game_id"]].removed
            ):
                continue

            values["name"] = item["title"]
            values["executable"] = (
                f"start heroic://launch/{app_name}"
                if os.name == "nt"
                else f"xdg-open heroic://launch/{app_name}"
            )
            values["hidden"] = False
            values["source"] = "heroic_sideload"
            values["added"] = current_time
            values["last_played"] = 0
            image_path = os.path.join(
                heroic_dir,
                "images-cache",
                hashlib.sha256(item["art_square"].encode()).hexdigest(),
            )
            if os.path.exists(image_path):
                save_cover(values, parent_widget, image_path)

            heroic_games[values["game_id"]] = values

    if not heroic_games:
        create_dialog(
            parent_widget,
            _("No Games Found"),
            _("No new games were found in the Heroic library."),
        )
    elif len(heroic_games) == 1:
        create_dialog(
            parent_widget,
            _("Heroic Games Imported"),
            _("Successfully imported 1 game."),
        )
    elif len(heroic_games) > 1:
        games_no = str(len(heroic_games))
        create_dialog(
            parent_widget,
            _("Heroic Games Imported"),
            # The variable is the number of games
            _(f"Successfully imported {games_no} games."),
        )
    return heroic_games
