# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import json
import time
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable
from contextlib import suppress
from gettext import gettext as _
from hashlib import sha256
from json import JSONDecodeError
from pathlib import Path
from typing import Any, override

from gi.repository import Gdk, GLib

from cartridges.games import Game

from . import APPDATA, APPLICATION_SUPPORT, CONFIG, FLATPAK, HOST_CONFIG, OPEN

ID, NAME = "heroic", _("Heroic")

_CONFIG_PATHS = (
    CONFIG / "heroic",
    HOST_CONFIG / "heroic",
    FLATPAK / "com.heroicgameslauncher.hgl" / "config" / "heroic",
    APPDATA / "heroic",
    APPLICATION_SUPPORT / "heroic",
)


class _Source(ABC):
    ID: str
    COVER_URI_PARAMS = ""
    LIBRARY_KEY = "library"

    @classmethod
    @abstractmethod
    def library_path(cls) -> Path: ...

    @classmethod
    def installed_app_names(cls) -> set[str] | None:
        return None


class _SideloadSource(_Source):
    ID = "sideload"
    LIBRARY_KEY = "games"

    @classmethod
    def library_path(cls) -> Path:
        return Path("sideload_apps", "library.json")


class _StoreSource(_Source):
    _INSTALLED_PATH: Path

    @classmethod
    def library_path(cls) -> Path:
        return Path("store_cache", f"{cls.ID}_library.json")

    @override
    @classmethod
    def installed_app_names(cls) -> set[str]:
        try:
            with (_config_dir() / cls._INSTALLED_PATH).open() as fp:
                data = json.load(fp)
        except (FileNotFoundError, JSONDecodeError):
            return set()

        return set(cls._installed(data))

    @staticmethod
    def _installed(data: Any) -> Generator[str]:  # noqa: ANN401
        with suppress(AttributeError):
            yield from data.keys()


class _LegendarySource(_StoreSource):
    ID = "legendary"
    COVER_URI_PARAMS = "?h=400&resize=1&w=300"
    _INSTALLED_PATH = Path("legendaryConfig", "legendary", "installed.json")


class _GOGSource(_StoreSource):
    ID = "gog"
    LIBRARY_KEY = "games"
    _INSTALLED_PATH = Path("gog_store", "installed.json")

    @override
    @staticmethod
    def _installed(data: Any) -> Generator[str]:
        with suppress(TypeError, KeyError):
            for entry in data["installed"]:
                with suppress(TypeError, KeyError):
                    yield entry["appName"]


class _NileSource(_StoreSource):
    ID = "nile"
    LIBRARY_PATH = Path("store_cache", "nile_library.json")
    _INSTALLED_PATH = Path("nile_config", "nile", "installed.json")

    @override
    @staticmethod
    def _installed(data: Any) -> Generator[str]:
        with suppress(TypeError):
            for entry in data:
                with suppress(TypeError, KeyError):
                    yield entry["id"]


def get_games(*, skip_ids: Iterable[str]) -> Generator[Game]:
    """Installed Heroic games."""
    added = int(time.time())
    for source in _LegendarySource, _GOGSource, _NileSource, _SideloadSource:
        yield from _games_from(source, added, skip_ids)


def _config_dir() -> Path:
    for path in _CONFIG_PATHS:
        if path.is_dir():
            return path

    raise FileNotFoundError


def _hidden_app_names() -> Generator[str]:
    try:
        with (_config_dir() / "store" / "config.json").open() as fp:
            config = json.load(fp)
    except (FileNotFoundError, JSONDecodeError):
        return

    with suppress(TypeError, KeyError):
        for game in config["games"]["hidden"]:
            with suppress(TypeError, KeyError):
                yield game["appName"]


def _games_from(
    source: type[_Source], added: int, skip_ids: Iterable[str]
) -> Generator[Game]:
    try:
        with (_config_dir() / source.library_path()).open() as fp:
            library = json.load(fp)
    except (FileNotFoundError, JSONDecodeError):
        return

    if not isinstance(library := library.get(source.LIBRARY_KEY), Iterable):
        return

    source_id = f"{ID}_{source.ID}"
    images_cache = _config_dir() / "images-cache"

    installed = source.installed_app_names()
    hidden = set(_hidden_app_names())

    for entry in library:
        with suppress(TypeError, KeyError):
            app_name = entry["app_name"]

            if (installed is not None) and (app_name not in installed):
                continue

            game_id = f"{source_id}_{app_name}"
            if game_id in skip_ids:
                continue

            cover_uri = f"{entry.get('art_square', '')}{source.COVER_URI_PARAMS}"
            cover_path = images_cache / sha256(cover_uri.encode()).hexdigest()

            try:
                cover = Gdk.Texture.new_from_filename(str(cover_path))
            except GLib.Error:
                cover = None

            yield Game(
                added=added,
                executable=f"{OPEN} heroic://launch/{entry['runner']}/{app_name}",
                game_id=game_id,
                source=source_id,
                hidden=app_name in hidden,
                name=entry["title"],
                developer=entry.get("developer"),
                cover=cover,
            )
