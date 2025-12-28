# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

import importlib
import os
import pkgutil
import sys
import time
from collections.abc import Generator
from contextlib import suppress
from pathlib import Path
from typing import Final, Protocol, cast

from gi.repository import GLib

from cartridges.games import Game

DATA = Path(GLib.get_user_data_dir())
CONFIG = Path(GLib.get_user_config_dir())
CACHE = Path(GLib.get_user_cache_dir())

FLATPAK = Path.home() / ".var" / "app"
HOST_DATA = Path(os.getenv("HOST_XDG_DATA_HOME", Path.home() / ".local" / "share"))
HOST_CONFIG = Path(os.getenv("HOST_XDG_CONFIG_HOME", Path.home() / ".config"))
HOST_CACHE = Path(os.getenv("HOST_XDG_CACHE_HOME", Path.home() / ".cache"))

PROGRAM_FILES_X86 = Path(os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
APPDATA = Path(os.getenv("APPDATA", r"C:\Users\Default\AppData\Roaming"))
LOCAL_APPDATA = Path(
    os.getenv("CSIDL_LOCAL_APPDATA", r"C:\Users\Default\AppData\Local")
)

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
    def get_games() -> Generator[Game]:
        """Installed games."""
        ...


def get_games() -> Generator[Game]:
    """Installed games from all sources."""
    added = int(time.time())
    for source in all_sources():
        with suppress(OSError):
            for game in source.get_games():
                game.added = game.added or added
                yield game


def all_sources() -> Generator[Source]:
    """All sources of games."""
    for module in pkgutil.iter_modules(__path__, prefix="."):
        yield cast(Source, importlib.import_module(module.name, __package__))
