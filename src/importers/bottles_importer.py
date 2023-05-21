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


def bottles_installed(win, path=None):
    location_key = "bottles-location"
    bottles_dir = (
        path if path else Path(shared.schema.get_string(location_key)).expanduser()
    )
    check = "library.yml"

    if not (bottles_dir / check).is_file():
        locations = (
            (Path(),)
            if path
            else (
                Path.home() / ".var/app/com.usebottles.bottles/data/bottles",
                win.data_dir / "bottles",
            )
        )

        bottles_dir = check_install(check, locations, (shared.schema, location_key))

    return bottles_dir


def bottles_importer(win):
    bottles_dir = bottles_installed(win)
    if not bottles_dir:
        return

    current_time = int(time())

    data = (bottles_dir / "library.yml").read_text("utf-8")

    library = yaml.load(data, Loader=yaml.Loader)

    importer = win.importer
    importer.total_queue += len(library)
    importer.queue += len(library)

    for game in library:
        game = library[game]
        values = {}

        values["game_id"] = f'bottles_{game["id"]}'

        if values["game_id"] in win.games and not win.games[values["game_id"]].removed:
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

        importer.save_game(
            values,
            (
                bottles_dir
                / "bottles"
                / game["bottle"]["path"]
                / "grids"
                / game["thumbnail"].split(":")[1]
            )
            if game["thumbnail"]
            else None,
        )
