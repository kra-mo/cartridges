# get_games.py
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
import shlex

from .game_data_to_json import game_data_to_json


def get_games(game_ids=None):
    games_dir = os.path.join(
        os.getenv("XDG_DATA_HOME")
        or os.path.expanduser(os.path.join("~", ".local", "share")),
        "cartridges",
        "games",
    )
    games = {}

    if not os.path.exists(games_dir):
        return {}

    if game_ids:
        game_files = [f"{game_id}.json" for game_id in game_ids]
    else:
        game_files = os.listdir(games_dir)

    for game in game_files:
        with open(os.path.join(games_dir, game), "r+") as open_file:
            data = json.loads(open_file.read())

            # Convert any outdated JSON values to our newest data format.
            needs_rewrite = False
            if "executable" in data and isinstance(data["executable"], str):
                needs_rewrite = True
                try:
                    # Use shell parsing to determine what the individual components are.
                    executable_split = shlex.split(
                        data["executable"], comments=False, posix=True
                    )
                except:
                    # Fallback: Split once at earliest space (1 part if no spaces, else 2 parts).
                    executable_split = data["executable"].split(" ", 1)
                data["executable"] = executable_split

            if needs_rewrite:
                open_file.seek(0)
                open_file.truncate()
                open_file.write(game_data_to_json(data))

            open_file.close()

            games[data["game_id"]] = data

    return games
