# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025-2026 kramo

# pyright: reportConstantRedefinition=false

import importlib
import os
import pkgutil
import sys
import time
from collections.abc import Generator, Iterable
from functools import cache
from pathlib import Path
from typing import Final, Protocol, cast

from gi.repository import Gio, GLib, GObject

from cartridges.games import Game

if Path("/.flatpak-info").exists():
    DATA = Path(os.getenv("HOST_XDG_DATA_HOME", Path.home() / ".local" / "share"))
    CONFIG = Path(os.getenv("HOST_XDG_CONFIG_HOME", Path.home() / ".config"))
    CACHE = Path(os.getenv("HOST_XDG_CACHE_HOME", Path.home() / ".cache"))
else:
    DATA = Path(GLib.get_user_data_dir())
    CONFIG = Path(GLib.get_user_config_dir())
    CACHE = Path(GLib.get_user_cache_dir())

FLATPAK = Path.home() / ".var" / "app"

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


class _SourceModule(Protocol):
    ID: Final[str]
    NAME: Final[str]

    @staticmethod
    def get_games() -> Generator[Game]:
        """Installed games."""
        ...


class Source(GObject.Object, Gio.ListModel):  # pyright: ignore[reportIncompatibleMethodOverride]
    """A source of games to import."""

    __gtype_name__ = __qualname__

    id = GObject.Property(type=str)
    name = GObject.Property(type=str)
    icon_name = GObject.Property(type=str)

    _module: _SourceModule

    def __init__(self, module: _SourceModule, added: int):
        super().__init__()

        self.id, self.name, self._module = module.ID, module.NAME, module
        self.bind_property(
            "id",
            self,
            "icon-name",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _, ident: f"{ident}-symbolic",
        )

        try:
            self._games = list(self._get_games(added))
        except OSError:
            self._games = []

    def do_get_item(self, position: int) -> Game | None:
        """Get the item at `position`."""
        try:
            return self._games[position]
        except IndexError:
            return None

    def do_get_item_type(self) -> type[Game]:
        """Get the type of the items in `self`."""
        return Game

    def do_get_n_items(self) -> int:
        """Get the number of items in `self`."""
        return len(self._games)

    def append(self, game: Game):
        """Append `game` to `self`."""
        pos = len(self._games)
        self._games.append(game)
        self.items_changed(pos, 0, 1)

    def _get_games(self, added: int) -> Generator[Game]:
        for game in self._module.get_games():
            game.added = game.added or added
            yield game


def load():
    """Populate `sources.model`."""
    model.splice(0, 0, tuple(_get_sources()))


@cache
def get(ident: str) -> Source:
    """Get the source with `ident`."""
    return next(s for s in cast(Iterable[Source], model) if s.id == ident)


def _get_sources() -> Generator[Source]:
    added = int(time.time())
    for info in pkgutil.iter_modules(__path__, prefix="."):
        module = cast(_SourceModule, importlib.import_module(info.name, __package__))
        yield Source(module, added)


model = Gio.ListStore(item_type=Source)
