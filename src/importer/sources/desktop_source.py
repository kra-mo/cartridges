# desktop_source.py
#
# Copyright 2023 kramo
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

import shlex
from hashlib import sha3_256
from pathlib import Path
from time import time
from typing import NamedTuple

from gi.repository import GLib, Gtk

from src import shared
from src.game import Game
from src.importer.sources.source import Source, SourceIterable


class DesktopSourceIterable(SourceIterable):
    source: "DesktopSource"

    def __iter__(self):
        """Generator method producing games"""

        added_time = int(time())

        icon_theme = Gtk.IconTheme.new()

        search_paths = [
            shared.home / ".local" / "share",
            "/run/host/usr/local/share",
            "/run/host/usr/share",
            "/run/host/usr/share/pixmaps",
            "/usr/share/pixmaps",
        ] + GLib.get_system_data_dirs()

        for search_path in search_paths:
            path = Path(search_path)

            if not str(search_path).endswith("/pixmaps"):
                path = path / "icons"

            if not path.is_dir():
                continue

            if str(path).startswith("/app/"):
                continue

            icon_theme.add_search_path(str(path))

        terminal_exec = self.get_terminal_exec()

        for path in search_paths:
            if str(path).startswith("/app/"):
                continue

            path = Path(path) / "applications"

            if not path.is_dir():
                continue

            for entry in path.iterdir():
                if entry.suffix != ".desktop":
                    continue

                # Skip Lutris games
                if str(entry.name).startswith("net.lutris."):
                    continue

                keyfile = GLib.KeyFile.new()

                try:
                    keyfile.load_from_file(str(entry), 0)

                    if "Game" not in keyfile.get_string_list(
                        "Desktop Entry", "Categories"
                    ):
                        continue

                    name = keyfile.get_string("Desktop Entry", "Name")
                    executable = keyfile.get_string("Desktop Entry", "Exec").split(
                        " %"
                    )[0]
                except GLib.GError:
                    continue

                # Skip Steam games
                if "steam://rungameid/" in executable:
                    continue

                # Skip Heroic games
                if "heroic://launch/" in executable:
                    continue

                # Skip Bottles games
                if "bottles-cli " in executable:
                    continue

                try:
                    if keyfile.get_boolean("Desktop Entry", "NoDisplay"):
                        continue
                except GLib.GError:
                    pass

                try:
                    terminal = keyfile.get_boolean("Desktop Entry", "Terminal")
                except GLib.GError:
                    terminal = False

                try:
                    cd_path = (
                        "cd " + keyfile.get_string("Desktop Entry", "Path") + " && "
                    )
                except GLib.GError:
                    cd_path = ""

                values = {
                    "source": self.source.source_id,
                    "added": added_time,
                    "name": name,
                    "game_id": "desktop_"
                    + sha3_256(
                        str(entry).encode("utf-8"), usedforsecurity=False
                    ).hexdigest(),
                    "executable": cd_path
                    + (
                        (terminal_exec + shlex.quote(executable))
                        if terminal
                        else executable
                    ),
                }
                game = Game(values)

                additional_data = {}

                try:
                    icon_str = keyfile.get_string("Desktop Entry", "Icon")
                except GLib.GError:
                    print("AAAAAAAAAAAAAAAAAAAAAAA")
                    yield game
                    continue
                else:
                    if "/" in icon_str:
                        additional_data = {"local_icon_path": Path(icon_str)}
                        yield (game, additional_data)
                        continue

                try:
                    if (
                        icon_path := icon_theme.lookup_icon(
                            icon_str,
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
                except GLib.GError:
                    pass

                yield (game, additional_data)

    def get_terminal_exec(self) -> str:
        match shared.schema.get_enum("desktop-terminal"):
            case 0:
                terminal_exec = shared.schema.get_string("desktop-terminal-custom-exec")
            case 1:
                terminal_exec = "xdg-terminal-exec"
            case 2:
                terminal_exec = "kgx -e"
            case 3:
                terminal_exec = "gnome-terminal --"
            case 4:
                terminal_exec = "konsole -e"
            case 5:
                terminal_exec = "xterm -e"
        return terminal_exec + " "


class DesktopLocations(NamedTuple):
    pass


class DesktopSource(Source):
    """Generic Flatpak source"""

    source_id = "desktop"
    name = _("Desktop")
    iterable_class = DesktopSourceIterable
    available_on = {"linux"}

    locations: DesktopLocations

    def __init__(self) -> None:
        super().__init__()
        self.locations = DesktopLocations()
