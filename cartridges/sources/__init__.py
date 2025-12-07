# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

import os
import sys
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Final, Protocol

from gi.repository import GLib

from cartridges.games import Game

DATA = Path(GLib.get_user_data_dir())
FLATPAK = Path.home() / ".var" / "app"
PROGRAM_FILES_X86 = Path(os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
APPLICATION_SUPPORT = Path.home() / "Library" / "Application Support"

OPEN = (
    "open"
    if sys.platform.startswith("darwin")
    else "start"
    if sys.platform.startswith("win32")
    else "xdg-open"
)


class Source(Protocol):
    """A source of games to import."""

    ID: Final[str]
    NAME: Final[str]

    @staticmethod
    def get_games(*, skip_ids: Iterable[str]) -> Generator[Game]:
        """Installed games, except those in `skip_ids`."""
        ...
