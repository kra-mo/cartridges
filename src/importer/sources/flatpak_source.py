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

from pathlib import Path
from time import time
from typing import NamedTuple

from gi.repository import GLib, Gtk

from src import shared
from src.game import Game
from src.importer.sources.location import Location, LocationSubPath
from src.importer.sources.source import ExecutableFormatSource, SourceIterable


class FlatpakSourceIterable(SourceIterable):
    source: "FlatpakSource"

    def __iter__(self):
        """Generator method producing games"""

        added_time = int(time())

        icon_theme = Gtk.IconTheme.new()
        icon_theme.add_search_path(str(self.source.locations.data["icons"]))

        blacklist = (
            {"hu.kramo.Cartridges", "hu.kramo.Cartridges.Devel"}
            if shared.schema.get_boolean("flatpak-import-launchers")
            else {
                "hu.kramo.Cartridges",
                "hu.kramo.Cartridges.Devel",
                "com.valvesoftware.Steam",
                "net.lutris.Lutris",
                "com.heroicgameslauncher.hgl",
                "com.usebottles.Bottles",
                "io.itch.itch",
                "org.libretro.RetroArch",
            }
        )

        for entry in (self.source.locations.data["applications"]).iterdir():
            if entry.suffix != ".desktop":
                continue

            keyfile = GLib.KeyFile.new()

            try:
                keyfile.load_from_file(str(entry), 0)

                if "Game" not in keyfile.get_string_list("Desktop Entry", "Categories"):
                    continue

                if (
                    flatpak_id := keyfile.get_string("Desktop Entry", "X-Flatpak")
                ) in blacklist or flatpak_id != entry.stem:
                    continue

                name = keyfile.get_string("Desktop Entry", "Name")

            except GLib.GError:
                continue

            values = {
                "source": self.source.source_id,
                "added": added_time,
                "name": name,
                "game_id": self.source.game_id_format.format(game_id=flatpak_id),
                "executable": self.source.make_executable(flatpak_id=flatpak_id),
            }
            game = Game(values)

            additional_data = {}

            try:
                if (
                    icon_path := icon_theme.lookup_icon(
                        keyfile.get_string("Desktop Entry", "Icon"),
                        None,
                        512,
                        1,
                        shared.win.get_direction(),
                        0,
                    )
                    .get_file()
                    .get_path()
                ):
                    additional_data = {"local_icon_path": Path(icon_path)}
                else:
                    pass
            except GLib.GError:
                pass

            yield (game, additional_data)


class FlatpakLocations(NamedTuple):
    data: Location


class FlatpakSource(ExecutableFormatSource):
    """Generic Flatpak source"""

    source_id = "flatpak"
    name = _("Flatpak")
    iterable_class = FlatpakSourceIterable
    executable_format = "flatpak run {flatpak_id}"
    available_on = {"linux"}

    locations: FlatpakLocations

    def __init__(self) -> None:
        super().__init__()
        self.locations = FlatpakLocations(
            Location(
                schema_key="flatpak-location",
                candidates=(
                    "/var/lib/flatpak/",
                    shared.data_dir / "flatpak",
                ),
                paths={
                    "applications": LocationSubPath("exports/share/applications", True),
                    "icons": LocationSubPath("exports/share/icons", True),
                },
                invalid_subtitle=Location.DATA_INVALID_SUBTITLE,
            )
        )
