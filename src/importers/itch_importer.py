# itch_importer.py
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
from pathlib import Path
from shutil import copyfile
from sqlite3 import connect
from time import time

import requests
from gi.repository import GdkPixbuf, Gio

from .check_install import check_install


def get_game(task, current_time, parent_widget, row):
    values = {}

    values["game_id"] = f"itch_{row[0]}"

    if (
        values["game_id"] in parent_widget.games
        and not parent_widget.games[values["game_id"]].removed
    ):
        task.return_value((None, None))
        return

    values["added"] = current_time
    values["executable"] = (
        ["start", f"itch://caves/{row[4]}/launch"]
        if os.name == "nt"
        else ["xdg-open", f"itch://caves/{row[4]}/launch"]
    )
    values["hidden"] = False
    values["last_played"] = 0
    values["name"] = row[1]
    values["source"] = "itch"

    if row[3] or row[2]:
        tmp_file = Gio.File.new_tmp(None)[0]
        try:
            with requests.get(row[3] or row[2], timeout=5) as cover:
                cover.raise_for_status()
                Path(tmp_file.get_path()).write_bytes(cover.content)
        except requests.exceptions.RequestException:
            task.return_value((values, None))
            return

        game_cover = GdkPixbuf.Pixbuf.new_from_stream_at_scale(
            tmp_file.read(), 2, 2, False
        ).scale_simple(*parent_widget.image_size, GdkPixbuf.InterpType.BILINEAR)

        itch_pixbuf = GdkPixbuf.Pixbuf.new_from_stream(tmp_file.read())
        itch_pixbuf = itch_pixbuf.scale_simple(
            parent_widget.image_size[0],
            itch_pixbuf.get_height()
            * (parent_widget.image_size[0] / itch_pixbuf.get_width()),
            GdkPixbuf.InterpType.BILINEAR,
        )
        itch_pixbuf.composite(
            game_cover,
            0,
            (parent_widget.image_size[1] - itch_pixbuf.get_height()) / 2,
            itch_pixbuf.get_width(),
            itch_pixbuf.get_height(),
            0,
            (parent_widget.image_size[1] - itch_pixbuf.get_height()) / 2,
            1.0,
            1.0,
            GdkPixbuf.InterpType.BILINEAR,
            255,
        )
    else:
        game_cover = None

    task.return_value((values, game_cover))


def get_games_async(parent_widget, rows, importer):
    current_time = int(time())

    # Wrap the function in another one as Gio.Task.run_in_thread does not allow for passing args
    def create_func(current_time, parent_widget, row):
        def wrapper(task, *_unused):
            get_game(
                task,
                current_time,
                parent_widget,
                row,
            )

        return wrapper

    def update_games(_task, result):
        final_values = result.propagate_value()[1]
        # No need for an if statement as final_value would be None for games we don't want to save
        importer.save_game(final_values[0], pixbuf=final_values[1])

    for row in rows:
        task = Gio.Task.new(None, None, update_games)
        task.run_in_thread(create_func(current_time, parent_widget, row))


def itch_importer(parent_widget):
    schema = parent_widget.schema
    location_key = "itch-location"
    itch_dir = Path(schema.get_string(location_key)).expanduser()
    check = Path("db") / "butler.db"

    if not (itch_dir / check).is_file():
        locations = (
            Path.home() / ".var" / "app" / "io.itch.itch" / "config" / "itch",
            parent_widget.config_dir / "itch",
        )

        if os.name == "nt":
            locations += (Path(os.getenv("appdata")) / "itch",)

        if not check_install(check, locations, (schema, location_key)):
            return

    database_path = (Path(schema.get_string(location_key)) / "db").expanduser()

    db_cache_dir = parent_widget.cache_dir / "cartridges" / "itch"
    db_cache_dir.mkdir(parents=True, exist_ok=True)

    # Copy the file because sqlite3 doesn't like databases in /run/user/
    database_tmp_path = db_cache_dir / "butler.db"

    for db_file in database_path.glob("butler.db*"):
        copyfile(db_file, (db_cache_dir / db_file.name))

    db_request = """
                SELECT
                    games.id,
                    games.title,
                    games.cover_url,
                    games.still_cover_url,
                    caves.id
                FROM
                    'caves'
                INNER JOIN
                    'games'
                ON
                    caves.game_id = games.id
                ;
            """

    connection = connect(database_tmp_path)
    cursor = connection.execute(db_request)
    rows = cursor.fetchall()
    connection.close()
    # No need to unlink temp files as they disappear when the connection is closed
    database_tmp_path.unlink(missing_ok=True)

    importer = parent_widget.importer
    importer.total_queue += len(rows)
    importer.queue += len(rows)

    get_games_async(parent_widget, rows, importer)
