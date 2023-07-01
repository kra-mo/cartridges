# flatpak_source.py
#
# Copyright 2022-2023 kramo
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
import subprocess
from pathlib import Path
from time import time

from gi.repository import Gtk

from src import shared
from src.game import Game
from src.importer.sources.location import Location
from src.importer.sources.source import Source, SourceIterationResult, SourceIterator


class FlatpakSourceIterator(SourceIterator):
    source: "FlatpakSource"

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games"""

        added_time = int(time())

        icon_theme = Gtk.IconTheme.new()
        icon_theme.add_search_path(str(self.source.data_location["icons"]))

        try:
            process = subprocess.run(
                ("flatpak-spawn", "--host", "flatpak", "list", "--columns=application"),
                capture_output=True,
                encoding="utf-8",
                check=True,
            )
            flatpak_ids = process.stdout.split("\n")

            to_remove = (
                {"hu.kramo.Cartridges"}
                if shared.schema.get_boolean("flatpak-import-launchers")
                else {
                    "hu.kramo.Cartridges",
                    "com.valvesoftware.Steam",
                    "net.lutris.Lutris",
                    "com.heroicgameslauncher.hgl",
                    "com.usebottles.Bottles",
                    "io.itch.itch",
                }
            )

            for item in to_remove:
                if item in flatpak_ids:
                    flatpak_ids.remove(item)

        except subprocess.CalledProcessError:
            return

        for entry in (self.source.data_location["applications"]).iterdir():
            flatpak_id = entry.stem

            if flatpak_id not in flatpak_ids:
                continue

            with entry.open("r", encoding="utf-8") as open_file:
                string = open_file.read()

            desktop_values = {"Name": None, "Icon": None, "Categories": None}
            for key in desktop_values:
                if regex := re.findall(f"{key}=(.*)\n", string):
                    desktop_values[key] = regex[0]

            if not desktop_values["Name"]:
                continue

            if not desktop_values["Categories"]:
                continue

            if not "Game" in desktop_values["Categories"].split(";"):
                continue

            values = {
                "source": self.source.id,
                "added": added_time,
                "name": desktop_values["Name"],
                "game_id": self.source.game_id_format.format(game_id=flatpak_id),
                "executable": self.source.executable_format.format(
                    flatpak_id=flatpak_id
                ),
            }
            game = Game(values)

            additional_data = {}
            if icon_name := desktop_values["Icon"]:
                if (
                    icon_path := icon_theme.lookup_icon(
                        icon_name, None, 512, 1, shared.win.get_direction(), 0
                    )
                    .get_file()
                    .get_path()
                ):
                    additional_data = {"local_icon_path": Path(icon_path)}
                else:
                    pass

            # Produce game
            yield (game, additional_data)


class FlatpakSource(Source):
    """Generic Flatpak source"""

    name = "Flatpak"
    iterator_class = FlatpakSourceIterator
    executable_format = "flatpak run {flatpak_id}"
    available_on = set(("linux",))

    data_location = Location(
        schema_key="flatpak-location",
        candidates=(
            "/var/lib/flatpak/exports/",
            shared.data_dir / "flatpak" / "exports",
        ),
        paths={
            "applications": (True, "share/applications"),
            "icons": (True, "share/icons"),
        },
    )
