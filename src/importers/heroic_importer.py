# heroic_importer.py
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
from pathlib import Path
from time import time

from .check_install import check_install


def heroic_importer(parent_widget):
    schema = parent_widget.schema
    location_key = "heroic-location"
    heroic_dir = Path(schema.get_string(location_key)).expanduser()
    check = "config.json"

    if not (heroic_dir / check).is_file():
        locations = (
            Path.home()
            / ".var"
            / "app"
            / "com.heroicgameslauncher.hgl"
            / "config"
            / "heroic",
            parent_widget.config_dir / "heroic",
        )

        if os.name == "nt":
            locations += (Path(os.getenv("appdata")) / "heroic",)

        heroic_dir = check_install(check, locations, (schema, location_key))
        if not heroic_dir:
            return

    schema = parent_widget.schema
    check = "config.json"

    current_time = int(time())

    importer = parent_widget.importer

    # Import Epic games
    if not schema.get_boolean("heroic-import-epic"):
        pass
    elif (heroic_dir / "store_cache" / "legendary_library.json").exists():
        data = (heroic_dir / "store_cache" / "legendary_library.json").read_text(
            "utf-8"
        )
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

                image_path = (
                    heroic_dir
                    / "images-cache"
                    / hashlib.sha256(
                        (f'{game["art_square"]}?h=400&resize=1&w=300').encode()
                    ).hexdigest()
                )

                importer.save_game(values, image_path if image_path.exists() else None)

        except KeyError:
            pass

    # Import GOG games
    if not schema.get_boolean("heroic-import-gog"):
        pass
    elif (heroic_dir / "gog_store" / "installed.json").exists():
        data = (heroic_dir / "gog_store" / "installed.json").read_text("utf-8")
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
            data = (heroic_dir / "gog_store" / "library.json").read_text("utf-8")
            library = json.loads(data)
            for game in library["games"]:
                if game["app_name"] == app_name:
                    values["developer"] = game["developer"]
                    values["name"] = game["title"]
                    image_path = (
                        heroic_dir
                        / "images-cache"
                        / hashlib.sha256(game["art_square"].encode()).hexdigest()
                    )

            values["executable"] = (
                ["start", f"heroic://launch/{app_name}"]
                if os.name == "nt"
                else ["xdg-open", f"heroic://launch/{app_name}"]
            )
            values["hidden"] = False
            values["source"] = "heroic_gog"
            values["added"] = current_time
            values["last_played"] = 0

            importer.save_game(values, image_path if image_path.exists() else None)

    # Import sideloaded games
    if not schema.get_boolean("heroic-import-sideload"):
        pass
    elif (heroic_dir / "sideload_apps" / "library.json").exists():
        data = (heroic_dir / "sideload_apps" / "library.json").read_text("utf-8")
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
            image_path = (
                heroic_dir
                / "images-cache"
                / hashlib.sha256(item["art_square"].encode()).hexdigest()
            )

            importer.save_game(values, image_path if image_path.exists() else None)
