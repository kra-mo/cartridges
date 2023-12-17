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
from typing import NamedTuple

from cartridges import shared
from cartridges.game import Game
from cartridges.importer.location import Location, LocationSubPath
from cartridges.importer.source import (
    ExecutableFormatSource,
    SourceIterable,
    SourceIterationResult,
)


class LegendarySourceIterable(SourceIterable):
    source: "LegendarySource"

    def game_from_library_entry(self, entry: dict) -> SourceIterationResult:
        # Skip non-games
        if entry["is_dlc"]:
            return None

        # Build game
        app_name = entry["app_name"]
        values = {
            "added": shared.import_time,
            "source": self.source.source_id,
            "name": entry["title"],
            "game_id": self.source.game_id_format.format(game_id=app_name),
            "executable": self.source.make_executable(app_name=app_name),
        }
        data = {}

        # Get additional metadata from file (optional)
        metadata_file = self.source.locations.config["metadata"] / f"{app_name}.json"
        try:
            metadata = json.load(metadata_file.open())
            values["developer"] = metadata["metadata"]["developer"]
            for image_entry in metadata["metadata"]["keyImages"]:
                if image_entry["type"] == "DieselGameBoxTall":
                    data["online_cover_url"] = image_entry["url"]
                    break
        except (JSONDecodeError, OSError, KeyError):
            pass

        game = Game(values)
        return (game, data)

    def __iter__(self):
        # Open library
        file = self.source.locations.config["installed.json"]
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


class LegendaryLocations(NamedTuple):
    config: Location


class LegendarySource(ExecutableFormatSource):
    source_id = "legendary"
    name = _("Legendary")
    executable_format = "legendary launch {app_name}"
    available_on = {"linux"}
    iterable_class = LegendarySourceIterable

    locations: LegendaryLocations

    def __init__(self) -> None:
        super().__init__()
        self.locations = LegendaryLocations(
            Location(
                schema_key="legendary-location",
                candidates=(
                    shared.config_dir / "legendary",
                    shared.host_config_dir / "legendary",
                ),
                paths={
                    "installed.json": LocationSubPath("installed.json"),
                    "metadata": LocationSubPath("metadata", True),
                },
                invalid_subtitle=Location.CONFIG_INVALID_SUBTITLE,
            )
        )
