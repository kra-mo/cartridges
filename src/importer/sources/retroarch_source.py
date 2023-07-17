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

import hashlib
import json
import logging
from json import JSONDecodeError
from pathlib import Path
from time import time

from src import shared
from src.errors.friendly_error import FriendlyError
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import Source, SourceIterationResult, SourceIterator


class RetroarchSourceIterator(SourceIterator):
    source: "RetroarchSource"

    def generator_builder(self) -> SourceIterationResult:
        # Get all playlist files, ending in .lpl
        playlist_files = self.source.config_location["playlists"].glob("*.lpl")

        bad_playlists = set()

        for playlist_file in playlist_files:
            try:
                with open(
                    self.source.config_location["playlists"] / playlist_file,
                    encoding="utf-8",
                ) as open_file:
                    playlist_json = json.load(open_file)
            except (JSONDecodeError, OSError, KeyError):
                logging.warning("Cannot read playlist file: %s", str(playlist_file))
                continue

            for item in playlist_json["items"]:
                # Select the core.
                # Try the content's core first, then the playlist's default core.
                # If none can be used, warn the user and continue.
                for core_path in (
                    item["core_path"],
                    playlist_json["default_core_path"],
                ):
                    if core_path not in ("DETECT", ""):
                        break
                else:
                    logging.warning("Cannot find core for: %s", str(item["path"]))
                    bad_playlists.add(playlist_file.stem)
                    continue

                # Build game
                game_id = hashlib.md5(item["path"].encode("utf-8")).hexdigest()

                values = {
                    "source": self.source.id,
                    "added": int(time()),
                    "name": item["label"],
                    "game_id": self.source.game_id_format.format(game_id=game_id),
                    "executable": self.source.executable_format.format(
                        rom_path=item["path"],
                        core_path=core_path,
                    ),
                }

                game = Game(values)
                additional_data = {}

                # Get boxart
                boxart_image_name = item["label"] + ".png"
                boxart_image_name = boxart_image_name.replace("&", "_")
                boxart_folder_name = playlist_file.name.split(".", 1)[0]
                image_path = (
                    self.source.config_location["thumbnails"]
                    / boxart_folder_name
                    / "Named_Boxarts"
                    / boxart_image_name
                )
                additional_data = {"local_image_path": image_path}

                yield (game, additional_data)

        if bad_playlists:
            raise FriendlyError(
                _("No RetroArch Core Selected"),
                # The variable is a newline separated list of playlists
                _("The following playlists have no default core:")
                + "\n\n{}\n\n".format("\n".join(bad_playlists))
                + _("Games with no core selected were not imported"),
            )


class RetroarchSource(Source):
    args = ' -L "{core_path}" "{rom_path}"'

    name = _("RetroArch")
    available_on = {"linux"}
    iterator_class = RetroarchSourceIterator

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

    @property
    def executable_format(self):
        self.config_location.resolve()
        is_flatpak = self.config_location.root.is_relative_to(shared.flatpak_dir)
        base = "flatpak run org.libretro.RetroArch" if is_flatpak else "retroarch"
        args = '-L "{core_path}" "{rom_path}"'
        return f"{base} {args}"
