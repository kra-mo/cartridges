# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import json
import os
import subprocess
from collections.abc import Generator
from json import JSONDecodeError
from pathlib import Path
from shlex import quote
from types import UnionType
from typing import Any

from gi.repository import Gdk, Gio, GLib, GObject, Gtk

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

        self.add_action_entries((
            ("play", lambda *_: self.play()),
            ("remove", lambda *_: setattr(self, "removed", True)),
        ))

        self.add_action(unhide_action := Gio.SimpleAction.new("unhide"))
        unhide_action.connect("activate", lambda *_: setattr(self, "hidden", False))
        hidden = Gtk.PropertyExpression.new(Game, None, "hidden")
        hidden.bind(unhide_action, "enabled", self)

        self.add_action(hide_action := Gio.SimpleAction.new("hide"))
        hide_action.connect("activate", lambda *_: setattr(self, "hidden", True))
        not_hidden = Gtk.ClosureExpression.new(bool, lambda _, h: not h, (hidden,))
        not_hidden.bind(hide_action, "enabled", self)

    def play(self):
        """Run the executable command in a shell."""
        if Path("/.flatpak-info").exists():
            executable = f"flatpak-spawn --host /bin/sh -c {quote(self.executable)}"
        else:
            executable = self.executable

        subprocess.Popen(  # noqa: S602
            executable,
            cwd=Path.home(),
            shell=True,
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

    def save(self):
        """Save the game's properties to disk."""
        properties = {name: getattr(self, name) for name in _PROPERTIES}

        _GAMES_DIR.mkdir(parents=True, exist_ok=True)
        path = (_GAMES_DIR / self.game_id).with_suffix(".json")
        with path.open(encoding="utf-8") as f:
            json.dump(properties, f, indent=4)


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
