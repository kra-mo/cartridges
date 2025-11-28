# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

from collections.abc import Generator
from pathlib import Path

from gi.repository import (
    Gio,
    GLib,
    GObject,
    Json,  # pyright: ignore[reportAttributeAccessIssue, reportUnknownVariableType]
)


GAMES_DIR = Path(GLib.get_user_data_dir(), "cartridges", "games")


class Game(GObject.Object):
    """Game data class."""

    __gtype_name__ = __qualname__

    added = GObject.Property(type=int)
    executable = GObject.Property(type=str)
    game_id = GObject.Property(type=str)
    source = GObject.Property(type=str)
    hidden = GObject.Property(type=bool, default=False)
    last_played = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str)
    developer = GObject.Property(type=str)
    removed = GObject.Property(type=bool, default=False)
    blacklisted = GObject.Property(type=bool, default=False)
    version = GObject.Property(type=float, default=2.0)


def load() -> Generator[Game]:
    """Load the user's games from disk."""
    for game in GAMES_DIR.iterdir():
        data = game.read_text("utf-8")
        try:
            yield Json.gobject_from_data(Game, data, len(data))
        except GLib.Error:
            continue


model = Gio.ListStore.new(Game)
model.splice(0, 0, tuple(load()))
