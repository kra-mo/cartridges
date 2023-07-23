# dolphin_source.py
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

from time import time

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import Source, SourceIterationResult, SourceIterator
from src.utils.dolphin_cache_reader import DolphinCacheReader


class DolphinIterator(SourceIterator):
    source: "DolphinSource"

    def generator_builder(self) -> SourceIterationResult:
        added_time = int(time())

        cache_reader = DolphinCacheReader(self.source.cache_location["cache_file"])
        games_data = cache_reader.get_games()

        for game_data in games_data:
            print(game_data["file_name"])

            # Build game
            game = Game(values)
            values = {
                "source": self.source.id,
                "added": added_time,
                #    "name": item["label"],
                #    "game_id": self.source.game_id_format.format(game_id=game_id),
                #    "executable": self.source.executable_format.format(
                #        rom_path=item["path"],
                #        core_path=core_path,
                #    ),
            }

            game = Game(values)
            additional_data = {}

            yield (game, additional_data)


class DolphinSource(Source):
    name = "Dolphin"
    available_on = {"linux"}
    iterator_class = DolphinIterator

    cache_location = Location(
        schema_key="dolphin-cache-location",
        candidates=(
            shared.flatpak_dir / "org.DolphinEmu.dolphin-emu" / "cache" / "dolphin-emu",
            shared.home / ".cache" / "dolphin-emu",
        ),
        paths={
            "cache_file": (False, "gamelist.cache"),
        },
    )

    @property
    def executable_format(self):
        self.config_location.resolve()
        is_flatpak = self.data_location.root.is_relative_to(shared.flatpak_dir)
        base = "flatpak run org.DolphinEmu.dolphin-emu" if is_flatpak else "dolphin-emu"
        args = '-e "{rom_path}"'
        return f"{base} {args}"
