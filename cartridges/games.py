# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import json
import os
import subprocess
from pathlib import Path
from shlex import quote
from types import UnionType
from typing import Any, NamedTuple, Self

from gi.repository import Gdk, Gio, GObject

from . import DATA_DIR


class _GameProp(NamedTuple):
    name: str
    type_: type | UnionType
    required: bool = False
    editable: bool = False


PROPERTIES: tuple[_GameProp, ...] = (
    _GameProp("added", int),
    _GameProp("executable", str | list[str], required=True, editable=True),
    _GameProp("game_id", str, required=True),
    _GameProp("source", str, required=True),
    _GameProp("hidden", bool),
    _GameProp("last_played", int),
    _GameProp("name", str, required=True, editable=True),
    _GameProp("developer", str, editable=True),
    _GameProp("removed", bool),
    _GameProp("blacklisted", bool),
    _GameProp("version", float),
)

GAMES_DIR = DATA_DIR / "games"
COVERS_DIR = DATA_DIR / "covers"

COVER_WIDTH = 200
COVER_HEIGHT = 300

_SPEC_VERSION = 2.0


class Game(Gio.SimpleActionGroup):
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

    cover = GObject.Property(type=Gdk.Paintable)

    @classmethod
    def from_data(cls, data: dict[str, Any]) -> Self:
        """Create a game from data. Useful for loading from JSON."""
        game = cls()

        for prop in PROPERTIES:
            value = data.get(prop.name)

            if not prop.required and value is None:
                continue

            if not isinstance(value, prop.type_):
                raise TypeError

            match prop.name:
                case "executable" if isinstance(value, list):
                    value = " ".join(value)
                case "version" if value and value > _SPEC_VERSION:
                    raise TypeError
                case "version":
                    continue

            setattr(game, prop.name, value)

        return game

    def play(self):
        """Run the executable command in a shell."""
        subprocess.Popen(  # noqa: S602
            get_executable(self.executable),
            cwd=Path.home(),
            shell=True,
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

    def save(self):
        """Save the game's properties to disk."""
        properties = {prop.name: getattr(self, prop.name) for prop in PROPERTIES}

        GAMES_DIR.mkdir(parents=True, exist_ok=True)
        path = (GAMES_DIR / self.game_id).with_suffix(".json")
        with path.open("w", encoding="utf-8") as f:
            json.dump(properties, f, indent=4, sort_keys=True)


def get_executable(executable: str) -> str:
    """Get the correct executable for the user's environment."""
    return (
        f"flatpak-spawn --host /bin/sh -c {quote(executable)}"
        if Path("/.flatpak-info").exists()
        else executable
    )
