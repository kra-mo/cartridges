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

from gi.repository import Gdk, Gio, GLib, GObject, Graphene, Gtk

from cartridges.games import COVER_HEIGHT, COVER_WIDTH, Game

if Path("/.flatpak-info").exists():
    SYSTEM_DATA = (
        Path("/run", "host", "usr", "share"),
        Path("/run", "host", "usr", "local", "share"),
    )
    DATA = Path(os.getenv("HOST_XDG_DATA_HOME", Path.home() / ".local" / "share"))
    CONFIG = Path(os.getenv("HOST_XDG_CONFIG_HOME", Path.home() / ".config"))
    CACHE = Path(os.getenv("HOST_XDG_CACHE_HOME", Path.home() / ".cache"))
else:
    SYSTEM_DATA = tuple(Path(path) for path in GLib.get_system_data_dirs())
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

_ICON_SIZE = 128


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


def cover_from_icon(theme: Gtk.IconTheme, name: str) -> Gdk.Paintable | None:
    """Get a cover from looking up `name` in `theme`."""
    icon = theme.lookup_icon(
        name,
        fallbacks=("application-x-executable",),
        size=_ICON_SIZE,
        # Sources shouldn't know about the user's display,
        # so we assume 2x scaling and render the icon at the correct size later.
        scale=2,
        direction=Gtk.TextDirection.NONE,
        flags=Gtk.IconLookupFlags.NONE,
    )
    snapshot = Gtk.Snapshot()
    snapshot.translate(
        Graphene.Point().init(
            (COVER_WIDTH - _ICON_SIZE) / 2,
            (COVER_HEIGHT - _ICON_SIZE) / 2,
        )
    )
    icon.snapshot(snapshot, _ICON_SIZE, _ICON_SIZE)
    return snapshot.to_paintable(Graphene.Size().init(COVER_WIDTH, COVER_HEIGHT))


def _get_sources() -> Generator[Source]:
    added = int(time.time())
    for info in pkgutil.iter_modules(__path__, prefix="."):
        module = cast(_SourceModule, importlib.import_module(info.name, __package__))
        yield Source(module, added)


model = Gio.ListStore(item_type=Source)
