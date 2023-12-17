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

import os
import shlex
import subprocess
from pathlib import Path
from typing import NamedTuple

from gi.repository import GLib, Gtk

from cartridges import shared
from cartridges.game import Game
from cartridges.importer.source import Source, SourceIterable


class DesktopSourceIterable(SourceIterable):
    source: "DesktopSource"

    def __iter__(self):
        """Generator method producing games"""

        icon_theme = Gtk.IconTheme.new()

        search_paths = [
            shared.host_data_dir,
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

        launch_command, full_path = self.check_launch_commands()

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
                except GLib.Error:
                    continue

                try:
                    try_exec = "which " + keyfile.get_string("Desktop Entry", "TryExec")
                    if not self.check_command(try_exec):
                        continue

                except GLib.Error:
                    pass

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
                except GLib.Error:
                    pass

                try:
                    if keyfile.get_boolean("Desktop Entry", "Hidden"):
                        continue
                except GLib.Error:
                    pass

                # Strip /run/host from Flatpak paths
                if entry.is_relative_to(prefix := "/run/host"):
                    entry = Path("/") / entry.relative_to(prefix)

                launch_arg = shlex.quote(str(entry if full_path else entry.stem))

                values = {
                    "source": self.source.source_id,
                    "added": shared.import_time,
                    "name": name,
                    "game_id": f"desktop_{entry.stem}",
                    "executable": f"{launch_command} {launch_arg}",
                }
                game = Game(values)

                additional_data = {}

                try:
                    icon_str = keyfile.get_string("Desktop Entry", "Icon")
                except GLib.Error:
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
                except GLib.Error:
                    pass

                yield (game, additional_data)

    def check_command(self, command) -> bool:
        flatpak_str = "flatpak-spawn --host /bin/sh -c "

        if os.getenv("FLATPAK_ID") == shared.APP_ID:
            command = flatpak_str + shlex.quote(command)

        try:
            subprocess.run(command, shell=True, check=True)
        except subprocess.CalledProcessError:
            return False

        return True

    def check_launch_commands(self) -> (str, bool):
        """Check whether `gio launch` `gtk4-launch` or `gtk-launch` are available on the system"""
        commands = (("gio launch", True), ("gtk4-launch", False), ("gtk-launch", False))

        for command, full_path in commands:
            # Even if `gio` is available, `gio launch` is only available on GLib >= 2.67.2
            command_to_check = (
                "gio help launch" if command == "gio launch" else f"which {command}"
            )

            if self.check_command(command_to_check):
                return command, full_path

        return commands[2]


class DesktopLocations(NamedTuple):
    pass


class DesktopSource(Source):
    """Generic Flatpak source"""

    source_id = "desktop"
    name = _("Desktop Entries")
    iterable_class = DesktopSourceIterable
    available_on = {"linux"}

    locations: DesktopLocations

    def __init__(self) -> None:
        super().__init__()
        self.locations = DesktopLocations()
