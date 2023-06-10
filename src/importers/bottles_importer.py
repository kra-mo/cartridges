# bottles_importer.py
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

from pathlib import Path
from time import time

import yaml

from . import shared
from .check_install import check_install


def bottles_installed(path=None):
    location_key = "bottles-location"
    check = "library.yml"

    locations = (
        (path,)
        if path
        else (
            Path(shared.schema.get_string(location_key)).expanduser(),
            Path.home() / ".var/app/com.usebottles.bottles/data/bottles",
            shared.data_dir / "bottles",
        )
    )

    bottles_dir = check_install(check, locations, (shared.schema, location_key))

    return bottles_dir


def bottles_importer():
    bottles_dir = bottles_installed()
    if not bottles_dir:
        return

    current_time = int(time())

    data = (bottles_dir / "library.yml").read_text("utf-8")

    library = yaml.safe_load(data)

    importer = shared.importer
    importer.total_queue += len(library)
    importer.queue += len(library)

    for game in library:
        game = library[game]
        values = {}

        values["game_id"] = f'bottles_{game["id"]}'

        if (
            values["game_id"] in shared.win.games
            and not shared.win.games[values["game_id"]].removed
        ):
            importer.save_game()
            continue

        values["name"] = game["name"]
        values["executable"] = [
            "xdg-open",
            f'bottles:run/{game["bottle"]["name"]}/{game["name"]}',
        ]
        values["hidden"] = False
        values["source"] = "bottles"
        values["added"] = current_time
        values["last_played"] = 0

        # This will not work if both Cartridges and Bottles are installed via Flatpak
        # as Cartridges can't access directories picked via Bottles' file picker portal
        try:
            bottles_location = Path(
                yaml.safe_load((bottles_dir / "data.yml").read_text("utf-8"))[
                    "custom_bottles_path"
                ]
            )
        except (FileNotFoundError, KeyError):
            bottles_location = bottles_dir / "bottles"

        grid_path = (
            bottles_location
            / game["bottle"]["path"]
            / "grids"
            / game["thumbnail"].split(":")[1]
        )

        importer.save_game(
            values,
            grid_path if game["thumbnail"] and grid_path.is_file() else None,
        )
