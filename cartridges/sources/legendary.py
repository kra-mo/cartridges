# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2026 kramo

import asyncio
import json
from collections.abc import Generator
from gettext import gettext as _
from json import JSONDecodeError
from pathlib import Path
from typing import cast
from urllib.request import urlopen

from gi.repository import Gdk, Gio, GLib

from cartridges.games import Game

from . import CONFIG

ID, NAME = "legendary", _("Legendary")

_CONFIG_PATH = CONFIG / "legendary"


def get_games() -> Generator[Game]:
    """Installed Legendary games."""
    config = _config_dir()

    try:
        with (config / "installed.json").open() as fp:
            installed = json.load(fp)
    except (OSError, JSONDecodeError):
        return

    if not isinstance(installed, dict):
        return

    app = cast(Gio.Application, Gio.Application.get_default())
    for entry in installed.values():
        if entry.get("is_dlc"):
            continue

        try:
            app_name = entry["app_name"]
            title = entry["title"]
        except KeyError:
            continue

        try:
            with (config / "metadata" / f"{app_name}.json").open() as fp:
                metadata = json.load(fp)["metadata"]
        except (KeyError, OSError, JSONDecodeError):
            metadata = {}

        game = Game(
            executable=f"legendary launch {app_name}",
            game_id=f"{ID}_{app_name}",
            source=ID,
            name=title,
            developer=metadata.get("developer"),
        )

        for image in metadata.get("keyImages", ()):
            if image.get("type") == "DieselGameBoxTall" and (url := image.get("url")):
                app.create_asyncio_task(_update_cover(game, url))
                break

        yield game


def _config_dir() -> Path:
    if _CONFIG_PATH.is_dir():
        return _CONFIG_PATH

    raise FileNotFoundError


async def _update_cover(game: Game, url: str):
    with await asyncio.to_thread(urlopen, url) as response:  # TODO: Rate limit?
        contents = response.read()

    game.cover = Gdk.Texture.new_from_bytes(GLib.Bytes.new(contents))
