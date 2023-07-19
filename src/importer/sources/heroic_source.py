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
from pathlib import Path
from time import time
from typing import Optional, TypedDict, Generator, Iterable
from abc import abstractmethod

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)


def path_json_load(path: Path):
    """
    Load JSON from the file at the given path

    :raises OSError: if the file can't be opened
    :raises JSONDecodeError: if the file isn't valid JSON
    """
    with path.open("r", encoding="utf-8") as open_file:
        return json.load(open_file)


class InvalidLibraryFileError(Exception):
    pass


class InvalidInstalledFileError(Exception):
    pass


class InvalidStoreFileError(Exception):
    pass


class HeroicLibraryEntry(TypedDict):
    app_name: str
    installed: Optional[bool]
    runner: str
    title: str
    developer: str
    art_square: str


class SubSource(Iterable):
    """Class representing a Heroic sub-source"""

    source: "HeroicSource"
    source_iterator: "HeroicSourceIterator"
    name: str
    service: str
    image_uri_params: str = ""
    relative_library_path: Path
    library_json_entries_key: str = "library"

    def __init__(self, source, source_iterator) -> None:
        self.source = source
        self.source_iterator = source_iterator

    @property
    def library_path(self) -> Path:
        return self.source.config_location.root / self.relative_library_path

    def process_library_entry(
        self, entry: HeroicLibraryEntry, added_time: int
    ) -> SourceIterationResult:
        """Build a Game from a Heroic library entry"""

        app_name = entry["app_name"]

        # Build game
        values = {
            "source": f"{self.source.id}_{self.service}",
            "added": added_time,
            "name": entry["title"],
            "developer": entry.get("developer", None),
            "game_id": self.source.game_id_format.format(
                service=self.service, game_id=app_name
            ),
            "executable": self.source.executable_format.format(app_name=app_name),
            "hidden": self.source_iterator.is_hidden(app_name),
        }
        game = Game(values)

        # Get the image path from the heroic cache
        # Filenames are derived from the URL that heroic used to get the file
        uri: str = entry["art_square"] + self.image_uri_params
        digest = sha256(uri.encode()).hexdigest()
        image_path = self.source.config_location.root / "images-cache" / digest
        additional_data = {"local_image_path": image_path}

        return (game, additional_data)

    def __iter__(self) -> Generator[SourceIterationResult, None, None]:
        """
        Iterate through the installed games with a generator
        :raises InvalidLibraryFileError: on initial call if the library file is bad
        """
        added_time = int(time())
        try:
            iterator = iter(
                path_json_load(self.library_path)[self.library_json_entries_key]
            )
        except (OSError, JSONDecodeError, TypeError, KeyError) as error:
            raise InvalidLibraryFileError(
                f"Invalid {self.library_path.name}"
            ) from error
        for entry in iterator:
            try:
                yield self.process_library_entry(entry, added_time)
            except KeyError as error:
                logging.warning(
                    "Skipped invalid %s game %s",
                    self.name,
                    entry.get("app_name", "UNKNOWN"),
                    exc_info=error,
                )
                continue


class StoreSubSource(SubSource):
    """
    Class representing a "store" sub source iterator.
    Games can be installed or not, this class does the check accordingly.
    """

    relative_installed_path: Optional[Path]
    installed_app_names: set[str]

    @property
    def installed_path(self) -> Path:
        return self.source.config_location.root / self.relative_installed_path

    @abstractmethod
    def get_installed_app_names(self) -> set[str]:
        """
        Get the sub source's installed app names as a set.

        :raises InvalidInstalledFileError: if the installed file data cannot be read
            Whenever possible, `__cause__` is set with the original exception
        """

    def is_installed(self, app_name: str) -> bool:
        return app_name in self.installed_app_names

    def process_library_entry(self, entry, added_time):
        # Skip games that are not installed
        app_name = entry["app_name"]
        if not self.is_installed(app_name):
            logging.warning(
                "Skipped %s game %s (%s): not installed",
                self.service,
                entry["title"],
                app_name,
            )
            return None
        # Process entry as normal
        return super().process_library_entry(entry, added_time)

    def __iter__(self):
        """
        Iterate through the installed games with a generator
        :raises InvalidLibraryFileError: on initial call if the library file is bad
        :raises InvalidInstalledFileError: on initial call if the installed file is bad
        """
        self.installed_app_names = self.get_installed_app_names()
        # TODO check that this syntax works
        yield from super()


class SideloadIterable(SubSource):
    name = "sideload"
    service = "sideload"
    relative_library_path = Path("sideload_apps") / "library.json"


class LegendaryIterable(StoreSubSource):
    name = "legendary"
    service = "epic"
    image_uri_params = "?h=400&resize=1&w=300"
    relative_library_path = Path("store_cache") / "legendary_library.json"

    # TODO simplify Heroic 2.9 has been out for a while
    # (uncomment value and remove the library_path property override)
    #
    # relative_installed_path = (
    #    Path("legendary") / "legendaryConfig" / "legendary" / "installed.json"
    # )
    relative_installed_path = None

    @property
    def library_path(self) -> Path:
        """Get the right path depending on the Heroic version"""
        heroic_config_path = self.source.config_location.root
        if (path := heroic_config_path / "legendaryConfig").is_dir():
            # Heroic >= 2.9
            pass
        else:
            # Heroic <= 2.8
            if heroic_config_path.is_relative_to(shared.flatpak_dir):
                # Heroic flatpak
                path = shared.flatpak_dir / "com.heroicgameslauncher.hgl" / "config"
            elif shared.config_dir.is_relative_to(shared.flatpak_dir):
                # Heroic native (from Cartridges flatpak)
                path = Path.home() / ".config"
            else:
                # Heroic native (from other Cartridges installations)
                path = shared.config_dir
        return path / "legendary" / "installed.json"

    def get_installed_app_names(self):
        try:
            return set(path_json_load(self.installed_path).keys())
        except (OSError, JSONDecodeError, AttributeError) as error:
            raise InvalidInstalledFileError(
                f"Invalid {self.installed_path.name}"
            ) from error


class GogIterable(StoreSubSource):
    name = "gog"
    service = "gog"
    library_json_entries_key = "games"
    relative_library_path = Path("store_cache") / "gog_library.json"
    relative_installed_path = Path("gog_store") / "installed.json"

    def get_installed_app_names(self):
        try:
            return {
                app_name
                for entry in path_json_load(self.installed_path)["installed"]
                if (app_name := entry.get("appName")) is not None
            }
        except (OSError, JSONDecodeError, KeyError, AttributeError) as error:
            raise InvalidInstalledFileError(
                f"Invalid {self.installed_path.name}"
            ) from error


class NileIterable(StoreSubSource):
    name = "nile"
    service = "amazon"
    relative_library_path = Path("store_cache") / "nile_library.json"
    relative_installed_path = Path("nile_config") / "nile" / "installed.json"

    def get_installed_app_names(self):
        try:
            installed_json = path_json_load(self.installed_path)
            return {
                app_name
                for entry in installed_json
                if (app_name := entry.get("id")) is not None
            }
        except (OSError, JSONDecodeError, AttributeError) as error:
            raise InvalidInstalledFileError(
                f"Invalid {self.installed_path.name}"
            ) from error


class HeroicSourceIterator(SourceIterator):
    source: "HeroicSource"

    hidden_app_names: set[str] = set()

    def is_hidden(self, app_name: str) -> bool:
        return app_name in self.hidden_app_names

    def __iter__(self):
        """Generator method producing games from all the Heroic sub-sources"""

        # Get the hidden app names
        try:
            store = path_json_load(self.source.config_location["store_config.json"])
            self.hidden_app_names = {
                game["appName"] for game in store["games"]["hidden"]
            }
        except (OSError, JSONDecodeError, KeyError, TypeError) as error:
            logging.error("Invalid Heroic store file", exc_info=error)
            raise InvalidStoreFileError() from error

        # Get games from the sub sources
        for sub_source_class in (
            SideloadIterable,
            LegendaryIterable,
            GogIterable,
            NileIterable,
        ):
            sub_source = sub_source_class(self.source, self)

            if not shared.schema.get_boolean("heroic-import-" + sub_source.service):
                logging.debug("Skipping Heroic %s: disabled", sub_source.service)
                continue

            try:
                sub_source_iterator = iter(sub_source)
            except (InvalidLibraryFileError, InvalidInstalledFileError) as error:
                logging.error(
                    "Skipping bad Heroic sub-source %s",
                    sub_source.service,
                    exc_info=error,
                )

            yield from sub_source_iterator


class HeroicSource(URLExecutableSource):
    """Generic Heroic Games Launcher source"""

    name = _("Heroic")
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
            "store_config.json": (False, ("store", "config.json")),
        },
    )

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.id + "_{service}_{game_id}"
