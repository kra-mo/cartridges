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
from abc import abstractmethod
from functools import cached_property
from hashlib import sha256
from json import JSONDecodeError
from pathlib import Path
from typing import Iterable, NamedTuple, Optional, TypedDict

from cartridges import shared
from cartridges.game import Game
from cartridges.importer.location import Location, LocationSubPath
from cartridges.importer.source import (
    SourceIterable,
    SourceIterationResult,
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


class SubSourceIterable(Iterable):
    """Class representing a Heroic sub-source"""

    source: "HeroicSource"
    source_iterable: "HeroicSourceIterable"
    name: str
    service: str
    image_uri_params: str = ""
    relative_library_path: Path
    library_json_entries_key: str = "library"

    def __init__(self, source, source_iterable) -> None:
        self.source = source
        self.source_iterable = source_iterable

    @cached_property
    def library_path(self) -> Path:
        path = self.source.locations.config.root / self.relative_library_path
        logging.debug("Using Heroic %s library.json path %s", self.name, path)
        return path

    def process_library_entry(self, entry: HeroicLibraryEntry) -> SourceIterationResult:
        """Build a Game from a Heroic library entry"""

        app_name = entry["app_name"]
        runner = entry["runner"]

        # Build game
        values = {
            "source": f"{self.source.source_id}_{self.service}",
            "added": shared.import_time,
            "name": entry["title"],
            "developer": entry.get("developer", None),
            "game_id": self.source.game_id_format.format(
                service=self.service, game_id=app_name
            ),
            "executable": self.source.make_executable(runner=runner, app_name=app_name),
            "hidden": self.source_iterable.is_hidden(app_name),
        }
        game = Game(values)

        # Get the image path from the Heroic cache
        # Filenames are derived from the URL that Heroic used to get the file
        uri: str = entry["art_square"] + self.image_uri_params
        digest = sha256(uri.encode()).hexdigest()
        image_path = self.source.locations.config.root / "images-cache" / digest
        additional_data = {"local_image_path": image_path}

        return (game, additional_data)

    def __iter__(self):
        """
        Iterate through the games with a generator
        :raises InvalidLibraryFileError: on initial call if the library file is bad
        """

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
                yield self.process_library_entry(entry)
            except KeyError as error:
                logging.warning(
                    "Skipped invalid %s game %s",
                    self.name,
                    entry.get("app_name", "UNKNOWN"),
                    exc_info=error,
                )
                continue


class StoreSubSourceIterable(SubSourceIterable):
    """
    Class representing a "store" sub source.
    Games can be installed or not, this class does the check accordingly.
    """

    relative_installed_path: Path
    installed_app_names: set[str]

    @cached_property
    def installed_path(self) -> Path:
        path = self.source.locations.config.root / self.relative_installed_path
        logging.debug("Using Heroic %s installed.json path %s", self.name, path)
        return path

    @abstractmethod
    def get_installed_app_names(self) -> set[str]:
        """
        Get the sub source's installed app names as a set.

        :raises InvalidInstalledFileError: if the installed file data cannot be read
            Whenever possible, `__cause__` is set with the original exception
        """

    def is_installed(self, app_name: str) -> bool:
        return app_name in self.installed_app_names

    def process_library_entry(self, entry):
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
        return super().process_library_entry(entry)

    def __iter__(self):
        """
        Iterate through the installed games with a generator
        :raises InvalidLibraryFileError: on initial call if the library file is bad
        :raises InvalidInstalledFileError: on initial call if the installed file is bad
        """
        self.installed_app_names = self.get_installed_app_names()
        yield from super().__iter__()


class SideloadIterable(SubSourceIterable):
    name = "sideload"
    service = "sideload"
    relative_library_path = Path("sideload_apps") / "library.json"
    library_json_entries_key = "games"


class LegendaryIterable(StoreSubSourceIterable):
    name = "legendary"
    service = "epic"
    image_uri_params = "?h=400&resize=1&w=300"
    relative_library_path = Path("store_cache") / "legendary_library.json"

    # relative_installed_path = (
    #    Path("legendary") / "legendaryConfig" / "legendary" / "installed.json"
    # )

    @cached_property
    def installed_path(self) -> Path:
        """Get the right path depending on the Heroic version"""
        # TODO after Heroic 2.9 has been out for a while
        # We should use the commented out relative_installed_path
        # and remove this property override.

        heroic_config_path = self.source.locations.config.root
        # Heroic >= 2.9
        if (path := heroic_config_path / "legendaryConfig").is_dir():
            logging.debug("Using Heroic >= 2.9 legendary file")
        # Heroic <= 2.8
        elif heroic_config_path.is_relative_to(shared.flatpak_dir):
            # Heroic flatpak
            path = shared.flatpak_dir / "com.heroicgameslauncher.hgl" / "config"
            logging.debug("Using Heroic flatpak <= 2.8 legendary file")
        else:
            # Heroic native
            logging.debug("Using Heroic native <= 2.8 legendary file")
            path = shared.host_config_dir

        path = path / "legendary" / "installed.json"
        logging.debug("Using Heroic %s installed.json path %s", self.name, path)
        return path

    def get_installed_app_names(self):
        try:
            return set(path_json_load(self.installed_path).keys())
        except (OSError, JSONDecodeError, AttributeError) as error:
            raise InvalidInstalledFileError(
                f"Invalid {self.installed_path.name}"
            ) from error


class GogIterable(StoreSubSourceIterable):
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


class NileIterable(StoreSubSourceIterable):
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


class HeroicSourceIterable(SourceIterable):
    source: "HeroicSource"

    hidden_app_names: set[str] = set()

    def is_hidden(self, app_name: str) -> bool:
        return app_name in self.hidden_app_names

    def get_hidden_app_names(self) -> set[str]:
        """Get the hidden app names from store/config.json

        :raises InvalidStoreFileError: if the store is invalid for some reason
        """

        try:
            store = path_json_load(self.source.locations.config["store_config.json"])
            self.hidden_app_names = {
                app_name
                for game in store["games"]["hidden"]
                if (app_name := game.get("appName")) is not None
            }
        except KeyError:
            logging.warning('No ["games"]["hidden"] key in Heroic store file')
        except (OSError, JSONDecodeError, TypeError) as error:
            logging.error("Invalid Heroic store file", exc_info=error)
            raise InvalidStoreFileError() from error

    def __iter__(self):
        """Generator method producing games from all the Heroic sub-sources"""

        self.get_hidden_app_names()

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
                sub_source_iterable = iter(sub_source)
                yield from sub_source_iterable
            except (InvalidLibraryFileError, InvalidInstalledFileError) as error:
                logging.error(
                    "Skipping bad Heroic sub-source %s",
                    sub_source.service,
                    exc_info=error,
                )
                continue


class HeroicLocations(NamedTuple):
    config: Location


class HeroicSource(URLExecutableSource):
    """Generic Heroic Games Launcher source"""

    source_id = "heroic"
    name = _("Heroic")
    iterable_class = HeroicSourceIterable
    url_format = "heroic://launch/{runner}/{app_name}"
    available_on = {"linux", "win32"}

    locations: HeroicLocations

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.source_id + "_{service}_{game_id}"

    def __init__(self) -> None:
        super().__init__()
        self.locations = HeroicLocations(
            Location(
                schema_key="heroic-location",
                candidates=(
                    shared.config_dir / "heroic",
                    shared.host_config_dir / "heroic",
                    shared.flatpak_dir
                    / "com.heroicgameslauncher.hgl"
                    / "config"
                    / "heroic",
                    shared.appdata_dir / "heroic",
                ),
                paths={
                    "config.json": LocationSubPath("config.json"),
                    "store_config.json": LocationSubPath("store/config.json"),
                },
                invalid_subtitle=Location.CONFIG_INVALID_SUBTITLE,
            )
        )
