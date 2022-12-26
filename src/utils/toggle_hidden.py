# toggle_hidden.py
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

def toggle_hidden(game):
    import os, json
    games_dir = os.path.join(os.environ.get("XDG_DATA_HOME"), "games")

    if os.path.exists(games_dir) == False:
        return

    file = open(os.path.join(games_dir, game + ".json"), "r")
    data = json.loads(file.read())
    file.close()
    file = open(os.path.join(games_dir, game + ".json"), "w")
    data["hidden"] = not data["hidden"]
    file.write(json.dumps(data, indent=4))
    file.close()
