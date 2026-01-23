# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023-2026 kramo
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

import itertools
import shlex
import subprocess
from collections.abc import Generator
from contextlib import suppress
from gettext import gettext as _
from pathlib import Path
from typing import cast

from gi.repository import GLib, Gtk

from cartridges import games
from cartridges.games import Game

from . import DATA, SYSTEM_DATA, cover_from_icon

ID, NAME = "desktop", _("Desktop")

_DATA_PATHS = (DATA, *SYSTEM_DATA)
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

_HIDDEN_KEYS = "NoDisplay", "Hidden"

_ICON_THEME = Gtk.IconTheme()


def get_games() -> Generator[Game]:
    """Installed desktop entries."""
    for path in itertools.chain.from_iterable(
        path.glob("*.desktop") for path in _DESKTOP_PATHS
    ):
        if any(path.match(pattern) for pattern in _FILE_BLACKLIST):
            continue

        with suppress(GLib.Error):
            file = GLib.KeyFile()
            file.load_from_file(str(path), GLib.KeyFileFlags.NONE)

            if "Game" not in file.get_string_list("Desktop Entry", "Categories"):
                continue

            for key in _HIDDEN_KEYS:
                with suppress(GLib.Error):
                    if file.get_boolean("Desktop Entry", key):
                        continue

            with suppress(GLib.Error):
                if not _try_exec(file.get_string("Desktop Entry", "TryExec")):
                    continue

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
                cover=cover_from_icon(
                    _ICON_THEME, file.get_string("Desktop Entry", "Icon")
                ),
            )


def _try_exec(executable: str) -> bool:
    try:
        subprocess.run(  # noqa: S603
            shlex.split(games.get_executable(f"which {executable}")),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        return False
    else:
        return True
