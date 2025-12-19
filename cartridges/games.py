# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import itertools
import json
import os
import subprocess
from collections.abc import Callable, Generator, Iterable
from gettext import gettext as _
from json import JSONDecodeError
from pathlib import Path
from shlex import quote
from types import UnionType
from typing import TYPE_CHECKING, Any, NamedTuple, Self, cast

from gi.repository import Gdk, Gio, GLib, GObject

from cartridges import DATA_DIR

if TYPE_CHECKING:
    from .application import Application
    from .ui.window import Window


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

_GAMES_DIR = DATA_DIR / "games"
_COVERS_DIR = DATA_DIR / "covers"

_SPEC_VERSION = 2.0
_MANUALLY_ADDED_ID = "imported"


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

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.add_action_entries((
            ("play", lambda *_: self.play()),
            ("remove", lambda *_: self._remove()),
        ))

        self.add_action(hide_action := Gio.SimpleAction.new("hide"))
        hide_action.connect("activate", lambda *_: self._hide())
        self.bind_property(
            "hidden",
            hide_action,
            "enabled",
            GObject.BindingFlags.SYNC_CREATE | GObject.BindingFlags.INVERT_BOOLEAN,
        )

        self.add_action(unhide_action := Gio.SimpleAction.new("unhide"))
        unhide_action.connect("activate", lambda *_: self._unhide())
        self.bind_property(
            "hidden",
            unhide_action,
            "enabled",
            GObject.BindingFlags.SYNC_CREATE,
        )

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

    @classmethod
    def for_editing(cls) -> Self:
        """Create a game for the user to manually set its properties."""
        return cls(
            game_id=f"{_MANUALLY_ADDED_ID}_{_increment_manually_added_id()}",
            source=_MANUALLY_ADDED_ID,
        )

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
        properties = {prop.name: getattr(self, prop.name) for prop in PROPERTIES}

        _GAMES_DIR.mkdir(parents=True, exist_ok=True)
        path = (_GAMES_DIR / self.game_id).with_suffix(".json")
        with path.open(encoding="utf-8") as f:
            json.dump(properties, f, indent=4)

    def _remove(self):
        self.removed = True
        self._send(
            _("{} removed").format(self.name),
            undo=lambda: setattr(self, "removed", False),
        )

    def _hide(self):
        self.hidden = True
        self._send(
            _("{} hidden").format(self.name),
            undo=lambda: setattr(self, "hidden", False),
        )

    def _unhide(self):
        self.hidden = False
        self._send(
            _("{} unhidden").format(self.name),
            undo=lambda: setattr(self, "hidden", True),
        )

    def _send(self, title: str, *, undo: Callable[[], Any]):
        app = cast("Application", Gio.Application.get_default())
        window = cast("Window", app.props.active_window)
        window.send_toast(title, undo=undo)


def _increment_manually_added_id() -> int:
    numbers = {
        game.game_id.split("_")[1]
        for game in cast(Iterable[Game], model)
        if game.game_id.startswith(_MANUALLY_ADDED_ID)
    }

    for count in itertools.count():
        if count not in numbers:
            return count

    raise ValueError


def load() -> Generator[Game]:
    """Load previously saved games from disk."""
    for path in _GAMES_DIR.glob("*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (JSONDecodeError, UnicodeDecodeError):
            continue

        try:
            game = Game.from_data(data)
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
