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

import os
import time

import yaml


def bottles_parser(parent_widget):
    schema = parent_widget.schema
    bottles_dir = os.path.expanduser(schema.get_string("bottles-location"))

    if not os.path.isfile(os.path.join(bottles_dir, "library.yml")):
        if os.path.exists(
            os.path.expanduser("~/.var/app/com.usebottles.bottles/data/bottles/")
        ):
            schema.set_string(
                "bottles-location", "~/.var/app/com.usebottles.bottles/data/bottles/"
            )
        elif os.path.exists(
            os.path.join(
                os.getenv("XDG_DATA_HOME")
                or os.path.expanduser(os.path.join("~", ".local", "share")),
                "bottles",
            )
        ):
            schema.set_string(
                "bottles-location",
                os.path.join(
                    os.getenv("XDG_DATA_HOME")
                    or os.path.expanduser(os.path.join("~", ".local", "share")),
                    "bottles",
                ),
            )
        else:
            return

    bottles_dir = os.path.expanduser(schema.get_string("bottles-location"))
    current_time = int(time.time())

    with open(os.path.join(bottles_dir, "library.yml"), "r") as open_file:
        data = open_file.read()

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
                os.path.join(
                    bottles_dir,
                    "bottles",
                    game["bottle"]["path"],
                    "grids",
                    game["thumbnail"].split(":")[1],
                ),
            )
        importer.save_game(values)
