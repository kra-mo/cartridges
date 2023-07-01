# itch_source.py
#
# Copyright 2022-2023 kramo
# Copyright 2023 Geoffrey Coulaud
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

from shutil import rmtree
from sqlite3 import connect
from time import time

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)
from src.utils.sqlite import copy_db


class ItchSourceIterator(SourceIterator):
    source: "ItchSource"

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games"""

        # Query the database
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
        db_path = copy_db(self.source.config_location["butler.db"])
        connection = connect(db_path)
        cursor = connection.execute(db_request)

        added_time = int(time())

        # Create games from the db results
        for row in cursor:
            values = {
                "added": added_time,
                "source": self.source.id,
                "name": row[1],
                "game_id": self.source.game_id_format.format(game_id=row[0]),
                "executable": self.source.executable_format.format(cave_id=row[4]),
            }
            additional_data = {"online_cover_url": row[3] or row[2]}
            game = Game(values)
            yield (game, additional_data)

        # Cleanup
        rmtree(str(db_path.parent))


class ItchSource(URLExecutableSource):
    name = "Itch"
    iterator_class = ItchSourceIterator
    url_format = "itch://caves/{cave_id}/launch"
    available_on = {"linux", "win32"}

    config_location = Location(
        schema_key="itch-location",
        candidates=(
            "~/.var/app/io.itch.itch/config/itch/",
            shared.config_dir / "itch",
            shared.appdata_dir / "itch",
        ),
        paths={"butler.db": (False, "db/butler.db")},
    )
