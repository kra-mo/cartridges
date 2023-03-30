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


def heroic_parser(parent_widget):
    schema = parent_widget.schema
    heroic_dir = os.path.expanduser(schema.get_string("heroic-location"))

    if not os.path.exists(os.path.join(heroic_dir, "config.json")):
        if os.path.exists(
            os.path.expanduser("~/.var/app/com.heroicgameslauncher.hgl/config/heroic/")
        ):
            schema.set_string(
                "heroic-location",
                "~/.var/app/com.heroicgameslauncher.hgl/config/heroic/",
            )
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
        elif os.name == "nt" and os.path.exists(
            os.path.join(os.getenv("appdata"), "heroic")
        ):
            schema.set_string(
                "heroic-location", os.path.join(os.getenv("appdata"), "heroic")
            )
        else:
            return

    heroic_dir = os.path.expanduser(schema.get_string("heroic-location"))
    current_time = int(time.time())

    importer = parent_widget.importer

    # Import Epic games
    if not schema.get_boolean("heroic-import-epic"):
        pass
    elif os.path.exists(os.path.join(heroic_dir, "lib-cache", "library.json")):
        with open(
            os.path.join(heroic_dir, "lib-cache", "library.json"), "r"
        ) as open_file:
            data = open_file.read()
        library = json.loads(data)

        try:
            for game in library["library"]:
                if not game["is_installed"]:
                    continue

                importer.total_queue += 1
                importer.queue += 1

                values = {}

                app_name = game["app_name"]
                values["game_id"] = f"heroic_epic_{app_name}"

                if (
                    values["game_id"] in parent_widget.games
                    and not parent_widget.games[values["game_id"]].removed
                ):
                    importer.save_game()
                    continue

                values["name"] = game["title"]
                values["developer"] = game["developer"]
                values["executable"] = (
                    ["start", f"heroic://launch/{app_name}"]
                    if os.name == "nt"
                    else ["xdg-open", f"heroic://launch/{app_name}"]
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
                    importer.save_cover(values["game_id"], image_path)

                importer.save_game(values)
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
        installed = json.loads(data)

        importer.total_queue += len(installed["installed"])
        importer.queue += len(installed["installed"])

        for item in installed["installed"]:
            values = {}
            app_name = item["appName"]

            values["game_id"] = f"heroic_gog_{app_name}"

            if (
                values["game_id"] in parent_widget.games
                and not parent_widget.games[values["game_id"]].removed
            ):
                importer.save_game()
                continue

            # Get game title and developer from library.json as they are not present in installed.json
            with open(
                os.path.join(heroic_dir, "gog_store", "library.json"), "r"
            ) as open_file:
                data = open_file.read()
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
                        importer.save_cover(values["game_id"], image_path)
                    break

            values["executable"] = (
                ["start", f"heroic://launch/{app_name}"]
                if os.name == "nt"
                else ["xdg-open", f"heroic://launch/{app_name}"]
            )
            values["hidden"] = False
            values["source"] = "heroic_gog"
            values["added"] = current_time
            values["last_played"] = 0

            importer.save_game(values)

    # Import sideloaded games
    if not schema.get_boolean("heroic-import-sideload"):
        pass
    elif os.path.exists(os.path.join(heroic_dir, "sideload_apps", "library.json")):
        with open(
            os.path.join(heroic_dir, "sideload_apps", "library.json"), "r"
        ) as open_file:
            data = open_file.read()
        library = json.loads(data)

        importer.total_queue += len(library["games"])
        importer.queue += len(library["games"])

        for item in library["games"]:
            values = {}
            app_name = item["app_name"]

            values["game_id"] = f"heroic_sideload_{app_name}"

            if (
                values["game_id"] in parent_widget.games
                and not parent_widget.games[values["game_id"]].removed
            ):
                importer.save_game()
                continue

            values["name"] = item["title"]
            values["executable"] = (
                ["start", f"heroic://launch/{app_name}"]
                if os.name == "nt"
                else ["xdg-open", f"heroic://launch/{app_name}"]
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
                importer.save_cover(values["game_id"], image_path)

            importer.save_game(values)
