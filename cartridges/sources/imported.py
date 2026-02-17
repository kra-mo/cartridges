# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

import itertools
import json
import time
from collections.abc import Generator
from gettext import gettext as _
from json import JSONDecodeError
from pathlib import Path

from gi.repository import Gdk, GLib

from cartridges.games import COVERS_DIR, GAMES_DIR, Game

ID, NAME = "imported", _("Added")


def get_games() -> Generator[Game]:
    """Manually added games."""
    for path in get_paths():
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except (JSONDecodeError, UnicodeDecodeError):
            continue

        try:
            game = Game.from_data(data)
        except TypeError:
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


def new() -> Game:
    """Create a new game for the user to manually set its properties."""
    numbers = {int(p.stem.rsplit("_", 1)[1]) for p in get_paths()}
    number = next(i for i in itertools.count() if i not in numbers)
    return Game(game_id=f"{ID}_{number}", source=ID, added=int(time.time()))


def get_paths() -> Generator[Path]:
    """Get the paths of all imported games on disk."""
    yield from GAMES_DIR.glob("imported_*.json")
