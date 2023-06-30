# steam_source.py
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

import re
from pathlib import Path
from time import time
from typing import Iterable

from src import shared
from src.game import Game
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)
from src.utils.steam import SteamFileHelper, SteamInvalidManifestError
from src.importer.sources.location import Location


class SteamSourceIterator(SourceIterator):
    source: "SteamSource"

    def get_manifest_dirs(self) -> Iterable[Path]:
        """Get dirs that contain steam app manifests"""
        libraryfolders_path = self.source.data_location["libraryfolders.vdf"]
        with open(libraryfolders_path, "r", encoding="utf-8") as file:
            contents = file.read()
        return [
            Path(path) / "steamapps"
            for path in re.findall('"path"\\s+"(.*)"\n', contents, re.IGNORECASE)
        ]

    def get_manifests(self) -> Iterable[Path]:
        """Get app manifests"""
        manifests = set()
        for steamapps_dir in self.get_manifest_dirs():
            if not steamapps_dir.is_dir():
                continue
            manifests.update(
                [
                    manifest
                    for manifest in steamapps_dir.glob("appmanifest_*.acf")
                    if manifest.is_file()
                ]
            )
        return manifests

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games"""
        appid_cache = set()
        manifests = self.get_manifests()

        added_time = int(time())

        for manifest in manifests:
            # Get metadata from manifest
            steam = SteamFileHelper()
            try:
                local_data = steam.get_manifest_data(manifest)
            except (OSError, SteamInvalidManifestError):
                continue

            # Skip non installed games
            installed_mask = 4
            if not int(local_data["stateflags"]) & installed_mask:
                continue

            # Skip duplicate appids
            appid = local_data["appid"]
            if appid in appid_cache:
                continue
            appid_cache.add(appid)

            # Build game from local data
            values = {
                "added": added_time,
                "name": local_data["name"],
                "source": self.source.id,
                "game_id": self.source.game_id_format.format(game_id=appid),
                "executable": self.source.executable_format.format(game_id=appid),
            }
            game = Game(values, allow_side_effects=False)

            # Add official cover image
            image_path = (
                self.source.data_location["librarycache"]
                / f"{appid}_library_600x900.jpg"
            )
            additional_data = {"local_image_path": image_path, "steam_appid": appid}

            # Produce game
            yield (game, additional_data)


class SteamSource(URLExecutableSource):
    name = "Steam"
    available_on = set(("linux", "win32"))
    iterator_class = SteamSourceIterator
    url_format = "steam://rungameid/{game_id}"

    data_location = Location(
        schema_key="steam-location",
        candidates=(
            "~/.var/app/com.valvesoftware.Steam/data/Steam/",
            shared.data_dir / "Steam",
            "~/.steam",
            shared.programfiles32_dir / "Steam",
        ),
        paths={
            "libraryfolders.vdf": (False, "steamapps/libraryfolders.vdf"),
            "librarycache": (True, "appcache/librarycache"),
        },
    )
