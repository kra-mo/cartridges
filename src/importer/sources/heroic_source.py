# heroic_source.py
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

import json
import logging
from hashlib import sha256
from json import JSONDecodeError
from time import time
from typing import Optional, TypedDict

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import (
    URLExecutableSource,
    SourceIterationResult,
    SourceIterator,
)


class HeroicLibraryEntry(TypedDict):
    app_name: str
    installed: Optional[bool]
    runner: str
    title: str
    developer: str
    art_square: str


class HeroicSubSource(TypedDict):
    service: str
    path: tuple[str]


class HeroicSourceIterator(SourceIterator):
    source: "HeroicSource"

    sub_sources: dict[str, HeroicSubSource] = {
        "sideload": {
            "service": "sideload",
            "path": ("sideload_apps", "library.json"),
        },
        "legendary": {
            "service": "epic",
            "path": ("store_cache", "legendary_library.json"),
        },
        "gog": {
            "service": "gog",
            "path": ("store_cache", "gog_library.json"),
        },
    }

    def game_from_library_entry(
        self, entry: HeroicLibraryEntry, added_time: int
    ) -> SourceIterationResult:
        """Helper method used to build a Game from a Heroic library entry"""

        # Skip games that are not installed
        if not entry["is_installed"]:
            return None

        # Build game
        app_name = entry["app_name"]
        runner = entry["runner"]
        service = self.sub_sources[runner]["service"]
        values = {
            "source": self.source.id,
            "added": added_time,
            "name": entry["title"],
            "developer": entry["developer"],
            "game_id": self.source.game_id_format.format(
                service=service, game_id=app_name
            ),
            "executable": self.source.executable_format.format(app_name=app_name),
        }
        game = Game(values)

        # Get the image path from the heroic cache
        # Filenames are derived from the URL that heroic used to get the file
        uri: str = entry["art_square"]
        if service == "epic":
            uri += "?h=400&resize=1&w=300"
        digest = sha256(uri.encode()).hexdigest()
        image_path = self.source.config_location.root / "images-cache" / digest
        additional_data = {"local_image_path": image_path}

        return (game, additional_data)

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games from all the Heroic sub-sources"""

        for sub_source in self.sub_sources.values():
            # Skip disabled sub-sources
            if not shared.schema.get_boolean("heroic-import-" + sub_source["service"]):
                continue
            # Load games from JSON
            file = self.source.config_location.root.joinpath(*sub_source["path"])
            try:
                library = json.load(file.open())["library"]
            except (JSONDecodeError, OSError, KeyError):
                # Invalid library.json file, skip it
                logging.warning("Couldn't open Heroic file: %s", str(file))
                continue

            added_time = int(time())

            for entry in library:
                try:
                    result = self.game_from_library_entry(entry, added_time)
                except KeyError:
                    # Skip invalid games
                    logging.warning("Invalid Heroic game skipped in %s", str(file))
                    continue
                yield result


class HeroicSource(URLExecutableSource):
    """Generic Heroic Games Launcher source"""

    name = "Heroic"
    iterator_class = HeroicSourceIterator
    url_format = "heroic://launch/{app_name}"
    available_on = {"linux", "win32"}

    config_location = Location(
        schema_key="heroic-location",
        candidates=(
            shared.flatpak_dir / "com.heroicgameslauncher.hgl" / "config" / "heroic",
            shared.config_dir / "heroic",
            shared.home / ".config" / "heroic",
            shared.appdata_dir / "heroic",
        ),
        paths={
            "config.json": (False, "config.json"),
        },
    )

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.name.lower() + "_{service}_{game_id}"
