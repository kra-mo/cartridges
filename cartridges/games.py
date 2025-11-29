# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import json
from collections.abc import Generator
from json import JSONDecodeError
from types import UnionType
from typing import Any

from gi.repository import Gdk, Gio, GLib, GObject

from cartridges import DATA_DIR

_GAMES_DIR = DATA_DIR / "games"
_COVERS_DIR = DATA_DIR / "covers"

_SPEC_VERSION = 2.0
_PROPERTIES: dict[str, tuple[type | UnionType, bool]] = {
    "added": (int, False),
    "executable": (str | list[str], True),
    "game_id": (str, True),
    "source": (str, True),
    "hidden": (bool, False),
    "last_played": (int, False),
    "name": (str, True),
    "developer": (str, False),
    "removed": (bool, False),
    "blacklisted": (bool, False),
    "version": (float, False),
}


class Game(GObject.Object):
    """Game data class."""

    __gtype_name__ = __qualname__

    added = GObject.Property(type=int)
    executable = GObject.Property(type=str)
    game_id = GObject.Property(type=str)
    source = GObject.Property(type=str)
    hidden = GObject.Property(type=bool, default=False)
    last_played = GObject.Property(type=int)
    name = GObject.Property(type=str)
    developer = GObject.Property(type=str)
    removed = GObject.Property(type=bool, default=False)
    blacklisted = GObject.Property(type=bool, default=False)
    version = GObject.Property(type=float, default=_SPEC_VERSION)

    cover = GObject.Property(type=Gdk.Texture)

    def __init__(self, data: dict[str, Any]):
        super().__init__()

        for name, (type_, required) in _PROPERTIES.items():
            value = data.get(name)

            if not required and value is None:
                continue

            if not isinstance(value, type_):
                raise TypeError

            match name:
                case "executable" if isinstance(value, list):
                    value = " ".join(value)
                case "version" if value and value > _SPEC_VERSION:
                    raise TypeError
                case "version":
                    continue

            setattr(self, name, value)


def _load() -> Generator[Game]:
    for path in _GAMES_DIR.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (JSONDecodeError, UnicodeDecodeError):
            continue

        try:
            game = Game(data)
        except TypeError:
            continue

        cover_path = _COVERS_DIR / game.game_id
        for ext in ".gif", ".tiff":
            filename = str(cover_path.with_suffix(ext))
            try:
                game.cover = Gdk.Texture.new_from_filename(filename)
            except GLib.Error:
                continue
            else:
                break

        yield game


model = Gio.ListStore.new(Game)
model.splice(0, 0, tuple(_load()))
