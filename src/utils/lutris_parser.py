# lutris_parser.py
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
import shutil
from sqlite3 import connect
from time import time


def lutris_parser(parent_widget):

    schema = parent_widget.schema

    database_path = os.path.join(
        os.path.expanduser(schema.get_string("lutris-location")), "pga.db"
    )
    if not os.path.isfile(database_path):
        if os.path.exists(
            os.path.expanduser("~/.var/app/net.lutris.Lutris/data/lutris/")
        ):
            schema.set_string(
                "lutris-location", "~/.var/app/net.lutris.Lutris/data/lutris/"
            )
        elif os.path.exists(
            os.path.join(
                os.getenv("XDG_DATA_HOME")
                or os.path.expanduser(os.path.join("~", ".local", "share")),
                "lutris",
            )
        ):
            schema.set_string(
                "lutris-location",
                os.path.join(
                    os.getenv("XDG_DATA_HOME")
                    or os.path.expanduser(os.path.join("~", ".local", "share")),
                    "lutris",
                ),
            )
        else:
            return

    cache_dir = os.path.expanduser(schema.get_string("lutris-cache-location"))
    if not os.path.exists(cache_dir):
        if os.path.exists(
            os.path.expanduser("~/.var/app/net.lutris.Lutris/cache/lutris/")
        ):
            schema.set_string(
                "lutris-cache-location", "~/.var/app/net.lutris.Lutris/cache/lutris/"
            )
        elif os.path.exists(
            os.path.join(
                os.getenv("XDG_CACHE_HOME")
                or os.path.expanduser(os.path.join("~", ".cache")),
                "lutris",
            )
        ):
            schema.set_string(
                "lutris-cache-location",
                os.path.join(
                    os.getenv("XDG_CACHE_HOME")
                    or os.path.expanduser(os.path.join("~", ".cache")),
                    "lutris",
                ),
            )
        else:
            return

    database_path = os.path.join(
        os.path.expanduser(schema.get_string("lutris-location")), "pga.db"
    )
    cache_dir = os.path.expanduser(schema.get_string("lutris-cache-location"))

    db_cache_dir = os.path.join(
        os.getenv("XDG_CACHE_HOME") or os.path.expanduser(os.path.join("~", ".cache")),
        "cartridges",
        "lutris",
    )
    os.makedirs(db_cache_dir, exist_ok=True)

    shutil.copyfile(database_path, os.path.join(db_cache_dir, "pga.db"))

    db_request = """
                SELECT
                    id, name, slug, runner, hidden
                FROM
                    'games'
                WHERE
                    name IS NOT NULL
                    AND slug IS NOT NULL
                    AND configPath IS NOT NULL
                    AND installed IS TRUE
                ;
            """

    connection = connect(os.path.join(db_cache_dir, "pga.db"))
    cursor = connection.execute(db_request)
    rows = cursor.fetchall()
    connection.close()

    if schema.get_boolean("steam"):
        rows = [row for row in rows if not row[3] == "steam"]

    current_time = int(time())

    importer = parent_widget.importer
    importer.total_queue += len(rows)
    importer.queue += len(rows)

    for row in rows:
        values = {}

        values["game_id"] = f"lutris_{row[3]}_{row[0]}"

        if (
            values["game_id"] in parent_widget.games
            and not parent_widget.games[values["game_id"]].removed
        ):
            importer.save_game()
            continue

        values["added"] = current_time
        values["executable"] = ["xdg-open", f"lutris:rungameid/{row[0]}"]
        values["hidden"] = row[4] == 1
        values["last_played"] = 0
        values["name"] = row[1]
        values["source"] = f"lutris_{row[3]}"

        if os.path.isfile(os.path.join(cache_dir, "coverart", f"{row[2]}.jpg")):
            importer.save_cover(
                values["game_id"], os.path.join(cache_dir, "coverart", f"{row[2]}.jpg")
            )

        importer.save_game(values)
