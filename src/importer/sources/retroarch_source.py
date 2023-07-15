# retroarch_source.py
#
# Copyright 2023 Rilic
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

import json
import os
import logging
from json import JSONDecodeError

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    Source
)


class RetroarchSourceIterator(SourceIterator):
    source: "RetroarchSource"

    def generator_builder(self) -> SourceIterationResult:
        playlist_files = []
        for file in os.listdir(self.source.config_location["playlists"]):
            if file.endswith('.lpl'):
                playlist_files.append(file)

        playlist_items = []
        for playlist_file in playlist_files:
            open_file = open(str(self.source.config_location["playlists"]) + "/" + playlist_file)
            try:
                playlist_json = json.load(open_file)
            except (JSONDecodeError, OSError, KeyError):
                logging.warning("Cannot read playlist file: %s", str(playlist_file))
                continue

            for item in playlist_json["items"]:
                # Select the core. Try the content's core first, then the playlist's
                # default core.
                core_path = item["core_path"]
                if core_path == "DETECT":
                    default_core = playlist_json["default_core_path"]
                    if default_core:
                        core_path = default_core
                    else:
                        logging.warning("Cannot find core for: %s", str(item["path"]))
                        continue

                # Build game
                game_title = item["label"].split("(", 1)[0]
                values = {
                    "source": self.source.id,
                    "added": int(time()),
                    "name": game_title,
                    "game_id": self.source.game_id_format.format(game_id=item["crc32"][:8]),
                    "executable": self.source.executable_format.format(
                        rom_path = item["path"],
                        core_path = core_path,
                    )
                }

                game = Game(values)
                additional_data = {}

                # Get boxart
                boxart_image_name = item["label"].split(".", 1)[0] + ".png"
                boxart_folder_name = playlist_file.split(".", 1)[0]
                image_path = self.source.config_location["thumbnails"] / boxart_folder_name / "Named_Boxarts" / boxart_image_name
                additional_data = {"local_image_path": image_path}

                yield(game, additional_data)


class RetroarchSource(Source):
    args = ' -L "{core_path}" "{rom_path}"'

    name = "Retroarch"
    available_on = {"linux"}
    iterator_class = RetroarchSourceIterator
    executable_format = 'retroarch' + args

    config_location = Location(
        schema_key="retroarch-location",
        candidates=(
            shared.flatpak_dir / "org.libretro.RetroArch" / "config" / "retroarch",
            shared.config_dir / "retroarch",
            shared.home / ".config" / "retroarch",
        ),
        paths={
            "playlists": (True, "playlists"),
            "thumbnails": (True, "thumbnails"),
        },
    )

    # Check if installation is flatpak'd.
    # TODO: There's probably a MUCH better way of doing this.
    # There's *is* a URI format, but it doesn't seem to work on the flatpak
    # version of Retroarch. https://github.com/libretro/RetroArch/pull/13563
    if str(shared.flatpak_dir) in str(config_location["playlists"]):
        executable_format = 'flatpak run org.libretro.RetroArch' + args
