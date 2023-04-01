# bottles_parser.py
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


def bottles_parser(parent_widget):
    schema = parent_widget.schema
    bottles_dir = Path(schema.get_string("bottles-location")).expanduser()

    if not (bottles_dir / "library.yml").is_file():
        if (
            Path("~/.var/app/com.usebottles.bottles/data/bottles/")
            .expanduser()
            .exists()
        ):
            schema.set_string(
                "bottles-location", "~/.var/app/com.usebottles.bottles/data/bottles/"
            )
        elif (parent_widget.data_dir / "bottles").exists():
            schema.set_string(
                "bottles-location", str(parent_widget.data_dir / "bottles")
            )
        else:
            return

    bottles_dir = Path(schema.get_string("bottles-location")).expanduser()
    current_time = int(time())

    data = (bottles_dir / "library.yml").read_text()

    library = yaml.load(data, Loader=yaml.Loader)

    importer = parent_widget.importer
    importer.total_queue += len(library)
    importer.queue += len(library)

    for game in library:
        game = library[game]
        values = {}

        values["game_id"] = f'bottles_{game["id"]}'

        if (
            values["game_id"] in parent_widget.games
            and not parent_widget.games[values["game_id"]].removed
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

        if game["thumbnail"]:
            importer.save_cover(
                values["game_id"],
                (
                    bottles_dir
                    / "bottles"
                    / game["bottle"]["path"]
                    / "grids"
                    / game["thumbnail"].split(":")[1]
                ),
            )
        importer.save_game(values)
