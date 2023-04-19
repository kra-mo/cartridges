# lutris_importer.py
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
from shutil import copyfile
from sqlite3 import connect
from time import time

from .check_install import check_install


def lutris_installed(win, path=None):
    location_key = "lutris-location"
    lutris_dir = (
        path if path else Path(win.schema.get_string(location_key)).expanduser()
    )
    check = "pga.db"

    if not (lutris_dir / check).is_file():
        locations = (
            (Path(),)
            if path
            else (
                Path.home() / ".var/app/net.lutris.Lutris/data/lutris",
                win.data_dir / "lutris",
            )
        )

        lutris_dir = check_install(check, locations, (win.schema, location_key))

    return lutris_dir


def lutris_cache_exists(win, path=None):
    cache_key = "lutris-cache-location"
    cache_dir = path if path else Path(win.schema.get_string(cache_key)).expanduser()
    cache_check = "coverart"

    if not (cache_dir / cache_check).exists():
        cache_locations = (
            (Path(),)
            if path
            else (
                Path.home() / ".var" / "app" / "net.lutris.Lutris" / "cache" / "lutris",
                win.cache_dir / "lutris",
            )
        )

        cache_dir = check_install(cache_check, cache_locations, (win.schema, cache_key))

    return cache_dir


def lutris_importer(win):
    lutris_dir = lutris_installed(win)
    if not lutris_dir:
        return

    cache_dir = lutris_cache_exists(win)
    if not cache_dir:
        return

    db_cache_dir = win.cache_dir / "cartridges" / "lutris"
    db_cache_dir.mkdir(parents=True, exist_ok=True)

    # Copy the file because sqlite3 doesn't like databases in /run/user/
    database_tmp_path = db_cache_dir / "pga.db"

    for db_file in lutris_dir.glob("pga.db*"):
        copyfile(db_file, (db_cache_dir / db_file.name))

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

    connection = connect(database_tmp_path)
    cursor = connection.execute(db_request)
    rows = cursor.fetchall()
    connection.close()
    # No need to unlink temp files as they disappear when the connection is closed
    database_tmp_path.unlink(missing_ok=True)

    if not win.schema.get_boolean("lutris-import-steam"):
        rows = [row for row in rows if not row[3] == "steam"]

    current_time = int(time())

    importer = win.importer
    importer.total_queue += len(rows)
    importer.queue += len(rows)

    for row in rows:
        values = {}

        values["game_id"] = f"lutris_{row[3]}_{row[0]}"

        if values["game_id"] in win.games and not win.games[values["game_id"]].removed:
            importer.save_game()
            continue

        values["added"] = current_time
        values["executable"] = ["xdg-open", f"lutris:rungameid/{row[0]}"]
        values["hidden"] = row[4] == 1
        values["last_played"] = 0
        values["name"] = row[1]
        values["source"] = f"lutris_{row[3]}"

        image_path = cache_dir / "coverart" / f"{row[2]}.jpg"
        importer.save_game(values, image_path if image_path.exists() else None)
