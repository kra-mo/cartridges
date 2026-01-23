# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

import functools
import itertools
from collections.abc import Generator
from contextlib import suppress
from gettext import gettext as _
from pathlib import Path

from gi.repository import GLib, Gtk

from cartridges.games import Game

from . import DATA, cover_from_icon

ID, NAME = "flatpak", _("Flatpak")

_PATHS = (
    Path("/var", "lib", "flatpak"),
    DATA / "flatpak",
)

_BLACKLIST = frozenset((
    "hu.kramo.Cartridges",
    "hu.kramo.Cartridges.Devel",
    "page.kramo.Cartridges",
    "page.kramo.Cartridges.Devel",
    "com.heroicgameslauncher.hgl",
    "com.usebottles.bottles",
    "com.valvesoftware.Steam",
    "io.itch.itch",
    "net.lutris.Lutris",
    "org.libretro.RetroArch",
))


def get_games() -> Generator[Game]:
    """Installed Flatpak games."""
    for path in itertools.chain.from_iterable(
        (path / "exports" / "share" / "applications").glob("*.desktop")
        for path in _PATHS
    ):
        with suppress(GLib.Error):
            file = GLib.KeyFile()
            file.load_from_file(str(path), GLib.KeyFileFlags.NONE)

            if "Game" not in file.get_string_list("Desktop Entry", "Categories"):
                continue

            flatpak_id = file.get_string("Desktop Entry", "X-Flatpak")
            if flatpak_id in _BLACKLIST:
                continue

            yield Game(
                executable=file.get_string("Desktop Entry", "Exec"),
                game_id=f"{ID}_{flatpak_id}",
                source=ID,
                name=file.get_string("Desktop Entry", "Name"),
                cover=cover_from_icon(_icon_theme(), flatpak_id),
            )


@functools.cache
def _icon_theme() -> Gtk.IconTheme:
    search_path = tuple(str(path / "exports" / "share" / "icons") for path in _PATHS)
    return Gtk.IconTheme(search_path=search_path)
