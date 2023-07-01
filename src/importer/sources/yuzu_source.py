# lutris_source.py
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
from time import time
from typing import Generator, Iterable
from configparser import ConfigParser
from pathlib import Path
import os

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    Source,
)


class YuzuSourceIterator(SourceIterator):
    source: "YuzuSource"

    extensions = (".xci", ".nsp", ".nso", ".nro")

    def iter_game_dirs(self) -> Iterable[tuple[bool, Path]]:
        """
        Get the rom directories from the parsed config

        The returned tuple indicates if the dir should be scanned recursively,
        then its path.
        """

        # Get the config data
        config = ConfigParser()
        if not config.read(
            self.source.data_location["qt-config.ini"], encoding="utf-8"
        ):
            return

        # Iterate through the dirs
        n_dirs = config.getint("UI", r"Paths\gamedirs\size", fallback=0)
        for i in range(1, n_dirs + 1):
            deep = config.getboolean(
                "UI", f"Paths\\gamedirs\\{i}\\deep_scan", fallback=False
            )
            path = Path(config.get("UI", f"Paths\\gamedirs\\{i}\\path", fallback=None))
            if path is None:
                continue
            yield deep, path

    def iter_rom_files(
        self, root: Path, recursive: bool = False
    ) -> Generator[Path, None, None]:
        """Generator method to iterate through rom files"""
        if not recursive:
            for path in root.iterdir():
                if not path.is_file():
                    continue
                if not path.suffix in self.extensions:
                    continue
                yield path
        else:
            for dir_path, _dirs, file_names in os.walk(root):
                for filename in file_names:
                    path = Path(dir_path) / filename
                    if path.suffix in self.extensions:
                        continue
                    yield path

    def generator_builder(self) -> Generator[SourceIterationResult, None, None]:
        """Generator method producing games"""

        added_time = int(time())

        # Get the games
        for recursive_search, game_dir in self.iter_game_dirs():
            for path in self.iter_rom_files(game_dir, recursive_search):
                values = {
                    # TODO add game_id
                    "added": added_time,
                    "source": self.source.id,
                    "executable": f"yuzu {str(path)}",  # HACK change depending on the variant
                }
                game = Game(values)
                additional_data = {}
                yield game, additional_data


class YuzuSource(Source):
    config_location = Location(
        "yuzu-location",
        (
            "~/.var/app/org.yuzu_emu.yuzu/config/yuzu",
            shared.config_dir / "yuzu",
            "~/.config/yuzu",
            # TODO windows path
        ),
        {"qt-config.ini": (False, "qt-config.ini")},
    )
