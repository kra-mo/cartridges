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

    if not game_ids:
        game_files = os.listdir(games_dir)
    else:
        game_files = []
        for game_id in game_ids:
            game_files.append(game_id + ".json")

    for game in game_files:
        with open(os.path.join(games_dir, game), "r") as open_file:
            data = json.loads(open_file.read())
            open_file.close()
        games[data["game_id"]] = data
    return games
