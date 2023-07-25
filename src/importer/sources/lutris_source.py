# lutris_source.py
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
from src.importer.sources.source import SourceIterable, URLExecutableSource
from src.utils.sqlite import copy_db


class LutrisSourceIterable(SourceIterable):
    source: "LutrisSource"

    def __iter__(self):
        """Generator method producing games"""

        # Query the database
        request = """
            SELECT id, name, slug, runner, hidden
            FROM 'games'
            WHERE
                name IS NOT NULL
                AND slug IS NOT NULL
                AND configPath IS NOT NULL
                AND installed
                AND (runner IS NOT "steam" OR :import_steam)
                AND (runner IS NOT "flatpak" OR :import_flatpak)
            ;
        """
        params = {
            "import_steam": shared.schema.get_boolean("lutris-import-steam"),
            "import_flatpak": shared.schema.get_boolean("lutris-import-flatpak"),
        }
        db_path = copy_db(self.source.data_location["pga.db"])
        connection = connect(db_path)
        cursor = connection.execute(request, params)

        added_time = int(time())

        # Create games from the DB results
        for row in cursor:
            # Create game
            values = {
                "added": added_time,
                "hidden": row[4],
                "name": row[1],
                "source": f"{self.source.id}_{row[3]}",
                "game_id": self.source.game_id_format.format(
                    runner=row[3], game_id=row[0]
                ),
                "executable": self.source.executable_format.format(game_id=row[0]),
            }
            game = Game(values)

            # Get official image path
            image_path = self.source.cache_location["coverart"] / f"{row[2]}.jpg"
            additional_data = {"local_image_path": image_path}

            # Produce game
            yield (game, additional_data)

        # Cleanup
        rmtree(str(db_path.parent))


class LutrisSource(URLExecutableSource):
    """Generic Lutris source"""

    name = _("Lutris")
    iterable_class = LutrisSourceIterable
    url_format = "lutris:rungameid/{game_id}"
    available_on = {"linux"}

    # FIXME possible bug: location picks ~/.var... and cache_lcoation picks ~/.local...

    data_location = Location(
        schema_key="lutris-location",
        candidates=(
            shared.flatpak_dir / "net.lutris.Lutris" / "data" / "lutris",
            shared.data_dir / "lutris",
            shared.home / ".local" / "share" / "lutris",
        ),
        paths={
            "pga.db": (False, "pga.db"),
        },
    )

    cache_location = Location(
        schema_key="lutris-cache-location",
        candidates=(
            shared.flatpak_dir / "net.lutris.Lutris" / "cache" / "lutris",
            shared.cache_dir / "lutris",
            shared.home / ".cache" / "lutris",
        ),
        paths={
            "coverart": (True, "coverart"),
        },
    )

    @property
    def game_id_format(self):
        return self.id + "_{runner}_{game_id}"
