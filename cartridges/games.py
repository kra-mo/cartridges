# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo

from collections.abc import Generator
from pathlib import Path
from typing import cast

from gi.repository import (
    Gdk,
    Gio,
    GLib,
    GObject,
    Json,  # pyright: ignore[reportAttributeAccessIssue]
)

DATA_DIR = Path(GLib.get_user_data_dir(), "cartridges")
GAMES_DIR = DATA_DIR / "games"
COVERS_DIR = DATA_DIR / "covers"


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

    cover = GObject.Property(type=Gdk.Texture)


def load() -> Generator[Game]:
    """Load the user's games from disk."""
    for path in GAMES_DIR.glob("*.json"):
        try:
            data = path.read_text("utf-8")
        except UnicodeError:
            continue

        try:
            game = cast(Game, Json.gobject_from_data(Game, data, len(data)))
        except GLib.Error:
            continue

        cover_path = COVERS_DIR / game.game_id
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
model.splice(0, 0, tuple(load()))
