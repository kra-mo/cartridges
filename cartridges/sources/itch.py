# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import asyncio
import sqlite3
from collections.abc import Generator
from gettext import gettext as _
from pathlib import Path
from typing import cast
from urllib.request import urlopen

from gi.repository import Gdk, Gio, GLib, Graphene, Gsk, Gtk

from cartridges.games import Game

from . import APPDATA, APPLICATION_SUPPORT, CONFIG, FLATPAK, HOST_CONFIG, OPEN

ID, NAME = "itch", _("itch")

_CONFIG_PATHS = (
    CONFIG / "itch",
    HOST_CONFIG / "itch",
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

_COVER_W = 200
_COVER_H = 300


def get_games() -> Generator[Game]:
    """Installed itch games."""
    butler = _config_dir() / "db" / "butler.db"
    app = cast(Gio.Application, Gio.Application.get_default())

    with sqlite3.connect(butler) as conn:
        for row in conn.execute(_QUERY):
            game = Game(
                executable=f"{OPEN} itch://caves/{row[4]}/launch",
                game_id=f"{ID}_{row[0]}",
                source=ID,
                name=row[1],
            )
            app.create_asyncio_task(  # pyright: ignore[reportAttributeAccessIssue]
                _update_cover(game, row[3] or row[2]),
            )
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


def _pad_cover(cover: Gdk.Texture) -> Gdk.Texture:
    app = cast(Gtk.Application, Gtk.Application.get_default())
    win = cast(Gtk.Native, app.props.active_window)
    renderer = cast(Gsk.Renderer, win.get_renderer())

    # TODO: Nicer Gsk wizardry
    downscaled = Gtk.Snapshot()
    cover.snapshot(downscaled, 3, 3)

    snapshot = Gtk.Snapshot()
    snapshot.append_scaled_texture(
        renderer.render_texture(cast(Gsk.RenderNode, downscaled.to_node())),
        Gsk.ScalingFilter.TRILINEAR,
        Graphene.Rect().init(0, 0, _COVER_W, _COVER_H),
    )

    if cover.props.height > cover.props.width:
        w, h = cover.props.width * (_COVER_H / cover.props.height), _COVER_H
        x, y = (_COVER_W - w) / 2, 0
    else:
        h, w = cover.props.height * (_COVER_W / cover.props.width), _COVER_W
        y, x = (_COVER_H - h) / 2, 0

    rect = Graphene.Rect().init(x, y, w, h)
    snapshot.append_scaled_texture(cover, Gsk.ScalingFilter.TRILINEAR, rect)
    return renderer.render_texture(cast(Gsk.RenderNode, snapshot.to_node()))
