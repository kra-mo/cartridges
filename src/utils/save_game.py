# save_game.py
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


def save_game(parent_widget, game):
    games_dir = parent_widget.data_dir / "cartridges" / "games"

    games_dir.mkdir(parents=True, exist_ok=True)

    (games_dir / f'{game["game_id"]}.json').write_text(
        json.dumps(game, indent=4, sort_keys=True), "utf-8"
    )
