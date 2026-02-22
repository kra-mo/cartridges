# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023-2026 kramo
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

import functools
import itertools
import shlex
import subprocess
from collections.abc import Generator
from contextlib import suppress
from gettext import gettext as _
from pathlib import Path
from typing import cast

from gi.repository import GLib, Gtk

from cartridges import cover, games
from cartridges.games import Game

from . import DATA, SYSTEM_DATA

ID, NAME = "desktop", _("Desktop")

_DATA_PATHS = (DATA, *SYSTEM_DATA)
_ICON_PATHS = tuple(path / "icons" for path in _DATA_PATHS)
_DESKTOP_PATHS = (
    Path(cast(str, GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DESKTOP))),
    *(path / "applications" for path in _DATA_PATHS),
)

_FILE_BLACKLIST = (
    "page.kramo.Cartridges.*",
    "net.lutris.*",
)
_EXECUTABLE_BLACKLIST = (
    "steam://rungameid/",
    "heroic://launch/",
    "bottles-cli ",
)
_FLATPAK_ID_BLACKLIST = frozenset((
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

_HIDDEN_KEYS = "NoDisplay", "Hidden"

_ICON_FALLBACK = "application-x-executable"


def get_games() -> Generator[Game]:
    """Installed desktop entries."""
    appids = set()
    for path in itertools.chain.from_iterable(
        path.glob("*.desktop") for path in _DESKTOP_PATHS
    ):
        appid = path.stem
        if appid in appids or any(path.match(pattern) for pattern in _FILE_BLACKLIST):
            continue

        with suppress(GLib.Error):
            file = GLib.KeyFile()
            file.load_from_file(str(path), GLib.KeyFileFlags.NONE)

            if "Game" not in file.get_string_list("Desktop Entry", "Categories"):
                continue

            flatpak_id = file.get_string("Desktop Entry", "X-Flatpak")
            if flatpak_id in _FLATPAK_ID_BLACKLIST:
                continue

            for key in _HIDDEN_KEYS:
                with suppress(GLib.Error):
                    if file.get_boolean("Desktop Entry", key):
                        continue

            with suppress(GLib.Error):
                if not _try_exec(file.get_string("Desktop Entry", "TryExec")):
                    continue

            try:
                icon_name = file.get_string("Desktop Entry", "Icon")
            except GLib.Error:
                icon_name = _ICON_FALLBACK

            icon = _icon_theme().lookup_icon(
                icon_name,
                fallbacks=(_ICON_FALLBACK,),
                size=cover.ICON_SIZE,
                # Sources shouldn't know about the user's display,
                # so we assume 2x scaling and render the icon at the correct size later.
                scale=2,
                direction=Gtk.TextDirection.NONE,
                flags=Gtk.IconLookupFlags.NONE,
            )

            real_path = (
                Path("/", path.relative_to("/run/host"))
                if path.is_relative_to("/run/host")
                else path
            )

            yield Game(
                executable=f"gio launch {shlex.quote(str(real_path))}",
                game_id=f"{ID}_{path.stem}",
                source=ID,
                name=file.get_string("Desktop Entry", "Name"),
                cover=cover.from_icon(icon),
            )
            appids.add(appid)


def _try_exec(executable: str) -> bool:
    try:
        subprocess.run(  # noqa: S603
            shlex.split(games.format_executable(f"which {executable}")),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return False
    else:
        return True


@functools.cache
def _icon_theme() -> Gtk.IconTheme:
    icon_theme = Gtk.IconTheme()
    search_path = icon_theme.props.search_path or []
    search_path += [str(path) for path in _ICON_PATHS if path not in search_path]
    icon_theme.props.search_path = search_path
    return icon_theme
