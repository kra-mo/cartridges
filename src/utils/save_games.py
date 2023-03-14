# save_games.py
#
# Copyright 2022 kramo
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

def save_games(games):
    import os, json

    games_dir = os.path.join(os.environ.get("XDG_DATA_HOME"), "cartridges", "games")
    existing = []

    if os.path.exists(games_dir) == False:
        os.makedirs(games_dir)

    for game in games:
        open_file = open(os.path.join(games_dir, game + ".json"), "w")
        open_file.write(json.dumps(games[game], indent=4, sort_keys=True))
        open_file.close()
