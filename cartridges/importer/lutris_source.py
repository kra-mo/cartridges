# lutris_source.py
#
# Copyright 2022-2024 kramo
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
from typing import NamedTuple

from cartridges import shared
from cartridges.game import Game
from cartridges.importer.location import Location, LocationSubPath
from cartridges.importer.source import SourceIterable, URLExecutableSource
from cartridges.utils.sqlite import copy_db


class LutrisSourceIterable(SourceIterable):
    source: "LutrisSource"

    def __iter__(self):
        """Generator method producing games"""

        # Query the database
        request = """
            SELECT
                games.id,
                games.name,
                games.slug,
                games.runner,
                categories.name = ".hidden" as hidden
            FROM
                games
            LEFT JOIN
                games_categories ON games_categories.game_id = games.id
            FULL JOIN
                categories ON games_categories.category_id = categories.id
            WHERE
                games.name IS NOT NULL
                AND games.slug IS NOT NULL
                AND games.configPath IS NOT NULL
                AND games.installed
                AND (games.runner IS NOT "steam" OR :import_steam)
                AND (games.runner IS NOT "flatpak" OR :import_flatpak)
            ;
        """

        params = {
            "import_steam": shared.schema.get_boolean("lutris-import-steam"),
            "import_flatpak": shared.schema.get_boolean("lutris-import-flatpak"),
        }
        db_path = copy_db(self.source.locations.data["pga.db"])
        connection = connect(db_path)
        cursor = connection.execute(request, params)
        coverart_is_dir = (
            coverart_path := self.source.locations.data.root / "coverart"
        ).is_dir()

        # Create games from the DB results
        for row in cursor:
            # Create game
            values = {
                "added": shared.import_time,
                "hidden": row[4],
                "name": row[1],
                "source": f"{self.source.source_id}_{row[3]}",
                "game_id": self.source.game_id_format.format(
                    runner=row[3], game_id=row[0]
                ),
                "executable": self.source.make_executable(game_id=row[0]),
            }
            game = Game(values)
            additional_data = {}

            # Get official image path
            if coverart_is_dir:
                image_path = coverart_path / f"{row[2]}.jpg"
                additional_data["local_image_path"] = image_path

            yield (game, additional_data)

        # Cleanup
        rmtree(str(db_path.parent))


class LutrisLocations(NamedTuple):
    data: Location


class LutrisSource(URLExecutableSource):
    """Generic Lutris source"""

    source_id = "lutris"
    name = _("Lutris")
    iterable_class = LutrisSourceIterable
    url_format = "lutris:rungameid/{game_id}"
    available_on = {"linux"}

    locations: LutrisLocations

    @property
    def game_id_format(self):
        return self.source_id + "_{runner}_{game_id}"

    def __init__(self) -> None:
        super().__init__()
        self.locations = LutrisLocations(
            Location(
                schema_key="lutris-location",
                candidates=(
                    shared.flatpak_dir / "net.lutris.Lutris" / "data" / "lutris",
                    shared.data_dir / "lutris",
                    shared.host_data_dir / "lutris",
                ),
                paths={
                    "pga.db": LocationSubPath("pga.db"),
                },
                invalid_subtitle=Location.DATA_INVALID_SUBTITLE,
            )
        )
