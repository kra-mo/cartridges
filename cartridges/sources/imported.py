# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

import json
from collections.abc import Generator
from gettext import gettext as _
from json import JSONDecodeError

from gi.repository import Gdk, GLib

from cartridges.games import COVERS_DIR, GAMES_DIR, Game

ID, NAME = "imported", _("Added")


def get_games() -> Generator[Game]:
    """Manually added games."""
    for path in GAMES_DIR.glob("imported_*.json"):
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
