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
from time import time

import yaml

from src import shared
from src.game import Game
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)
from src.utils.decorators import (
    replaced_by_path,
    replaced_by_schema_key,
)


class BottlesSourceIterator(SourceIterator):
    source: "BottlesSource"

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games"""

        data = (self.source.location / "library.yml").read_text("utf-8")
        library: dict = yaml.safe_load(data)

        for entry in library.values():
            # Build game
            values = {
                "version": shared.SPEC_VERSION,
                "source": self.source.id,
                "added": int(time()),
                "name": entry["name"],
                "game_id": self.source.game_id_format.format(game_id=entry["id"]),
                "executable": self.source.executable_format.format(
                    bottle_name=entry["bottle"]["name"], game_name=entry["name"]
                ),
            }
            game = Game(values, allow_side_effects=False)

            # Get official cover path
            try:
                # This will not work if both Cartridges and Bottles are installed via Flatpak
                # as Cartridges can't access directories picked via Bottles' file picker portal
                bottles_location = Path(
                    yaml.safe_load(
                        (self.source.location / "data.yml").read_text("utf-8")
                    )["custom_bottles_path"]
                )
            except (FileNotFoundError, KeyError):
                bottles_location = self.source.location / "bottles"

            bottle_path = entry["bottle"]["path"]
            image_name = entry["thumbnail"].split(":")[1]
            image_path = bottles_location / bottle_path / "grids" / image_name
            additional_data = {"local_image_path": image_path}

            # Produce game
            yield (game, additional_data)


class BottlesSource(URLExecutableSource):
    """Generic Bottles source"""

    name = "Bottles"
    iterator_class = BottlesSourceIterator
    url_format = 'bottles:run/"{bottle_name}"/"{game_name}"'
    available_on = set(("linux",))

    @property
    @replaced_by_schema_key
    @replaced_by_path("~/.var/app/com.usebottles.bottles/data/bottles/")
    @replaced_by_path(shared.data_dir / "bottles")
    def location(self) -> Path:
        raise FileNotFoundError()
