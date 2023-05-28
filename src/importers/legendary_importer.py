# legendary_importer.py
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
from pathlib import Path
import requests
import tempfile
from time import time

from . import shared
from .check_install import check_install


def legendary_installed(path=None):
    location_key = "legendary-location"
    check = "installed.json"

    locations = (
        (path,)
        if path
        else (
            Path(shared.schema.get_string(location_key)).expanduser(),
        )
    )

    legendary_dir = check_install(check, locations, (shared.schema, location_key))

    return legendary_dir

def legendary_importer():
    legendary_dir = legendary_installed()
    if not legendary_dir:
        return

    current_time = int(time())
    importer = shared.importer

    games = json.load((legendary_dir / "installed.json").open())

    values = {}

    glist = list(games.values())
    for gameid in glist:
        if gameid["is_dlc"]:
            pass
        else:
            gamejson = gameid["app_name"] + ".json"
            gamemetadata = json.load((legendary_dir / "metadata" / gamejson).open())
            values["name"] = gameid["title"]
            values["developer"] = gamemetadata["metadata"]["developer"]
            values["executable"] = "legendary launch " + gameid["app_name"]
            values["hidden"] = False
            values["source"] = "legendary"
            values["game_id"] = f"legendary_{gameid['app_name']}"
            values["added"] = current_time
            values["last_played"] = 0

            for image in gamemetadata["metadata"]["keyImages"]:
                if image["type"] != "DieselGameBoxTall":
                    continue
                else:
                    gameimg = requests.get(image["url"]).content
                    with tempfile.NamedTemporaryFile(delete=False) as tmp:
                        tmp.write(gameimg)
                    image_path = Path(tmp.name)

            if not (
                values["game_id"] in shared.win.games
                and not shared.win.games[values["game_id"]].removed
            ):
                importer.save_game(values, image_path if image_path.is_file() else None)
