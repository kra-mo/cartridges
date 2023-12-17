# bottles_source.py
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

from pathlib import Path
from typing import NamedTuple

import yaml

from cartridges import shared
from cartridges.game import Game
from cartridges.importer.location import Location, LocationSubPath
from cartridges.importer.source import SourceIterable, URLExecutableSource


class BottlesSourceIterable(SourceIterable):
    source: "BottlesSource"

    def __iter__(self):
        """Generator method producing games"""

        data = self.source.locations.data["library.yml"].read_text("utf-8")
        library: dict = yaml.safe_load(data)

        for entry in library.values():
            # Build game
            values = {
                "source": self.source.source_id,
                "added": shared.import_time,
                "name": entry["name"],
                "game_id": self.source.game_id_format.format(game_id=entry["id"]),
                "executable": self.source.make_executable(
                    bottle_name=entry["bottle"]["name"],
                    game_name=entry["name"],
                ),
            }
            game = Game(values)

            # Get official cover path
            try:
                # This will not work if both Cartridges and Bottles are installed via Flatpak
                # as Cartridges can't access directories picked via Bottles' file picker portal
                bottles_location = Path(
                    yaml.safe_load(
                        self.source.locations.data["data.yml"].read_text("utf-8")
                    )["custom_bottles_path"]
                )
            except (FileNotFoundError, KeyError):
                bottles_location = self.source.locations.data.root / "bottles"

            bottle_path = entry["bottle"]["path"]

            additional_data = {}
            if entry["thumbnail"]:
                image_name = entry["thumbnail"].split(":")[1]
                image_path = bottles_location / bottle_path / "grids" / image_name
                additional_data = {"local_image_path": image_path}

            yield (game, additional_data)


class BottlesLocations(NamedTuple):
    data: Location


class BottlesSource(URLExecutableSource):
    """Generic Bottles source"""

    source_id = "bottles"
    name = _("Bottles")
    iterable_class = BottlesSourceIterable
    url_format = 'bottles:run/"{bottle_name}"/"{game_name}"'
    available_on = {"linux"}

    locations: BottlesLocations

    def __init__(self) -> None:
        super().__init__()
        self.locations = BottlesLocations(
            Location(
                schema_key="bottles-location",
                candidates=(
                    shared.flatpak_dir / "com.usebottles.bottles" / "data" / "bottles",
                    shared.data_dir / "bottles/",
                    shared.host_data_dir / "bottles",
                ),
                paths={
                    "library.yml": LocationSubPath("library.yml"),
                    "data.yml": LocationSubPath("data.yml"),
                },
                invalid_subtitle=Location.DATA_INVALID_SUBTITLE,
            )
        )
