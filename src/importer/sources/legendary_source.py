# legendary_source.py
#
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

import json
import logging
from json import JSONDecodeError
from pathlib import Path
from time import time
from typing import Generator

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import Source, SourceIterationResult, SourceIterator


class LegendarySourceIterator(SourceIterator):
    source: "LegendarySource"

    def game_from_library_entry(self, entry: dict) -> SourceIterationResult:
        # Skip non-games
        if entry["is_dlc"]:
            return None

        # Build game
        app_name = entry["app_name"]
        values = {
            "version": shared.SPEC_VERSION,
            "added": int(time()),
            "source": self.source.id,
            "name": entry["title"],
            "game_id": self.source.game_id_format.format(game_id=app_name),
            "executable": self.source.executable_format.format(app_name=app_name),
        }
        data = {}

        # Get additional metadata from file (optional)
        metadata_file = self.source.data_location["metadata"] / f"{app_name}.json"
        try:
            metadata = json.load(metadata_file.open())
            values["developer"] = metadata["metadata"]["developer"]
            for image_entry in metadata["metadata"]["keyImages"]:
                if image_entry["type"] == "DieselGameBoxTall":
                    data["online_cover_url"] = image_entry["url"]
                    break
        except (JSONDecodeError, OSError, KeyError):
            pass

        game = Game(values, allow_side_effects=False)
        return (game, data)

    def generator_builder(self) -> Generator[SourceIterationResult, None, None]:
        # Open library
        file = self.source.data_location["installed.json"]
        try:
            library: dict = json.load(file.open())
        except (JSONDecodeError, OSError):
            logging.warning("Couldn't open Legendary file: %s", str(file))
            return
        # Generate games from library
        for entry in library.values():
            try:
                result = self.game_from_library_entry(entry)
            except KeyError as error:
                # Skip invalid games
                logging.warning(
                    "Invalid Legendary game skipped in %s", str(file), exc_info=error
                )
                continue
            yield result


class LegendarySource(Source):
    name = "Legendary"
    executable_format = "legendary launch {app_name}"
    available_on = set(("linux", "win32"))

    iterator_class = LegendarySourceIterator
    data_location: Location = Location(
        candidates=(
            lambda: shared.schema.get_string("legendary-location"),
            shared.config_dir / "legendary/",
            "~/.config/legendary",
        ),
        paths={
            "installed.json": (False, "installed.json"),
            "metadata": (True, "metadata"),
        },
    )
