# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2022-2026 kramo

import asyncio
import sqlite3
from collections.abc import Generator
from gettext import gettext as _
from pathlib import Path
from typing import cast
from urllib.request import urlopen

from gi.repository import Gdk, Gio, GLib, Graphene, Gtk

from cartridges.games import COVER_HEIGHT, COVER_WIDTH, Game

from . import APPDATA, APPLICATION_SUPPORT, CONFIG, FLATPAK, OPEN

ID, NAME = "itch", _("itch")

_CONFIG_PATHS = (
    CONFIG / "itch",
    FLATPAK / "io.itch.itch" / "config" / "itch",
    APPDATA / "itch",
    APPLICATION_SUPPORT / "itch",
)

_QUERY = """
    SELECT
        games.id,
        games.title,
        games.cover_url,
        games.still_cover_url,
        caves.id
    FROM caves
    INNER JOIN games
    ON caves.game_id = games.id;"""


def get_games() -> Generator[Game]:
    """Installed itch games."""
    app = cast(Gio.Application, Gio.Application.get_default())
    with sqlite3.connect(_config_dir() / "db" / "butler.db") as conn:
        for row in conn.execute(_QUERY):
            game = Game(
                executable=f"{OPEN} itch://caves/{row[4]}/launch",
                game_id=f"{ID}_{row[0]}",
                source=ID,
                name=row[1],
            )
            app.create_asyncio_task(_update_cover(game, row[3] or row[2]))  # pyright: ignore[reportAttributeAccessIssue]
            yield game


def _config_dir() -> Path:
    for path in _CONFIG_PATHS:
        if path.is_dir():
            return path

    raise FileNotFoundError


async def _update_cover(game: Game, url: str):
    with await asyncio.to_thread(urlopen, url) as response:  # TODO: Rate limit?
        contents = response.read()

    game.cover = _pad_cover(Gdk.Texture.new_from_bytes(GLib.Bytes.new(contents)))


def _pad_cover(cover: Gdk.Paintable) -> Gdk.Paintable | None:
    if cover.props.height > cover.props.width:
        w, h = cover.props.width * (COVER_HEIGHT / cover.props.height), COVER_HEIGHT
        x, y = (COVER_WIDTH - w) / 2, 0
    else:
        h, w = cover.props.height * (COVER_WIDTH / cover.props.width), COVER_WIDTH
        y, x = (COVER_HEIGHT - h) / 2, 0

    snapshot = Gtk.Snapshot()
    snapshot.translate(Graphene.Point().init(x, y))
    cover.snapshot(snapshot, w, h)
    return snapshot.to_paintable(Graphene.Size().init(COVER_WIDTH, COVER_HEIGHT))
