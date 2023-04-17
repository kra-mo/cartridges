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


def get_games(win, game_ids=None):
    games = {}

    if not win.games_dir.exists():
        return {}

    game_files = (
        [win.games_dir / f"{game_id}.json" for game_id in game_ids]
        if game_ids
        else win.games_dir.iterdir()
    )

    for open_file in game_files:
        data = json.load(open_file.open())
        games[data["game_id"]] = data

    return games
