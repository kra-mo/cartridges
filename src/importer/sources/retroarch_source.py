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

import json
import logging
import re
from hashlib import md5
from json import JSONDecodeError
from pathlib import Path
from time import time
from typing import NamedTuple

from urllib.parse import quote

from src import shared
from src.errors.friendly_error import FriendlyError
from src.game import Game
from src.importer.sources.location import (
    Location,
    LocationSubPath,
    UnresolvableLocationError,
)
from src.importer.sources.source import Source, SourceIterable
from src.importer.sources.steam_source import SteamSource


class RetroarchSourceIterable(SourceIterable):
    source: "RetroarchSource"

    def get_config_value(self, key: str, config_data: str):
        for item in re.findall(f'{key}\\s*=\\s*"(.*)"\n', config_data, re.IGNORECASE):
            if item.startswith(":"):
                item = item.replace(":", str(self.source.locations.config.root))

            logging.debug(str(item))
            return item

        raise KeyError(f"Key not found in RetroArch config: {key}")

    def __iter__(self):
        added_time = int(time())
        bad_playlists = set()

        config_file = self.source.locations.config["retroarch.cfg"]
        with config_file.open(encoding="utf-8") as open_file:
            config_data = open_file.read()

        playlist_folder = Path(
            self.get_config_value("playlist_directory", config_data)
        ).expanduser()
        thumbnail_folder = Path(
            self.get_config_value("thumbnails_directory", config_data)
        ).expanduser()

        # Get all playlist files, ending in .lpl
        playlist_files = playlist_folder.glob("*.lpl")

        for playlist_file in playlist_files:
            logging.debug(playlist_file)
            try:
                with playlist_file.open(
                    encoding="utf-8",
                ) as open_file:
                    playlist_json = json.load(open_file)
            except (JSONDecodeError, OSError):
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
                game_id = md5(item["path"].encode("utf-8")).hexdigest()

                values = {
                    "source": self.source.source_id,
                    "added": added_time,
                    "name": item["label"],
                    "game_id": self.source.game_id_format.format(game_id=game_id),
                    "executable": self.source.make_executable(
                        rom_path=item["path"],
                        core_path=core_path,
                    ),
                }

                game = Game(values)

                # Get boxart
                boxart_image_name = item["label"] + ".png"
                boxart_image_name = re.sub(r"[&\*\/:`<>\?\\\|]", "_", boxart_image_name)
                boxart_folder_name = playlist_file.stem
                image_path = (
                    thumbnail_folder
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


class RetroarchLocations(NamedTuple):
    config: Location


class RetroarchSource(Source):
    name = _("RetroArch")
    source_id = "retroarch"
    available_on = {"linux"}
    iterable_class = RetroarchSourceIterable

    locations = RetroarchLocations(
        Location(
            schema_key="retroarch-location",
            candidates=[
                shared.flatpak_dir / "org.libretro.RetroArch" / "config" / "retroarch",
                shared.config_dir / "retroarch",
                shared.home / ".config" / "retroarch",
                # TODO: Windows support, waiting for executable path setting improvement
                # Path("C:\\RetroArch-Win64"),
                # Path("C:\\RetroArch-Win32"),
                # TODO: UWP support (URL handler - https://github.com/libretro/RetroArch/pull/13563)
                # shared.local_appdata_dir
                # / "Packages"
                # / "1e4cf179-f3c2-404f-b9f3-cb2070a5aad8_8ngdn9a6dx1ma"
                # / "LocalState",
            ],
            paths={
                "retroarch.cfg": LocationSubPath("retroarch.cfg"),
            },
            invalid_subtitle=Location.CONFIG_INVALID_SUBTITLE,
        )
    )

    def __init__(self) -> None:
        super().__init__()
        try:
            self.locations.config.candidates.append(self.get_steam_location())
        except (OSError, KeyError, UnresolvableLocationError):
            logging.debug("Steam isn't installed")
        except ValueError as error:
            logging.debug("RetroArch Steam location candiate not found", exc_info=error)

    def get_steam_location(self) -> str:
        """
        Get the RetroArch installed via Steam location

        :raise UnresolvableLocationError: if steam isn't installed
        :raise KeyError: if there is no libraryfolders.vdf subpath
        :raise OSError: if libraryfolders.vdf can't be opened
        :raise ValueError: if RetroArch isn't installed through Steam
        """

        # Find steam location
        libraryfolders = SteamSource().locations.data["libraryfolders.vdf"]
        parse_apps = False
        with open(libraryfolders, "r", encoding="utf-8") as open_file:
            # Search each line for a library path and store it each time a new one is found.
            for line in open_file:
                if '"path"' in line:
                    library_path = re.findall(
                        '"path"\\s+"(.*)"\n', line, re.IGNORECASE
                    )[0]
                elif '"apps"' in line:
                    parse_apps = True
                elif parse_apps and "}" in line:
                    parse_apps = False
                # Stop searching, as the library path directly above the appid has been found.
                elif parse_apps and '"1118310"' in line:
                    return Path(f"{library_path}/steamapps/common/RetroArch")
        # Not found
        raise ValueError("RetroArch not found in Steam library")

    def make_executable(self, rom_path: Path, core_path: Path) -> str:
        """
        Generate an executable command from the rom path and core path,
        depending on the source's location.

        The format depends on RetroArch's installation method,
        detected from the source config location

        :param Path rom_path: the game's rom path
        :param Path core_path: the game's core path
        :return str: an executable command
        """

        self.locations.config.resolve()
        args = f'-L "{core_path}" "{rom_path}"'

        # Steam RetroArch
        # (Must check before Flatpak, because Steam itself can be installed as one)
        if self.locations.config.root.parent.parent.name == "steamapps":
            uri = "steam://run/1118310//" + quote(args) + "/"
            return f"xdg-open {uri}"

        # Flatpak RetroArch
        if self.locations.config.root.is_relative_to(shared.flatpak_dir):
            return f"flatpak run org.libretro.RetroArch {args}"

        # TODO executable override for non-sandboxed sources

        # Linux native RetroArch
        return f"retroarch {args}"

        # TODO implement for windows (needs override)
