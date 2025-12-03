# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import itertools
import re
import time
from collections.abc import Generator, Iterable
from pathlib import Path

from gi.repository import Gdk, GLib

from cartridges.games import Game

from . import APPLICATION_SUPPORT, DATA, FLATPAK, OPEN, PROGRAM_FILES_X86

ID: str = "steam"

_INSTALLED_MASK = 4
_CAPSULE_NAMES = "library_600x900.jpg", "library_capsule.jpg"
_DATA_PATHS = (
    Path.home() / ".steam" / "steam",
    DATA / "Steam",
    FLATPAK / "com.valvesoftware.Steam" / "data" / "Steam",
    PROGRAM_FILES_X86 / "Steam",
    APPLICATION_SUPPORT / "Steam",
)


def get_games(*, skip_ids: Iterable[str]) -> Generator[Game]:
    """Installed Steam games."""
    added = int(time.time())
    librarycache = _data_dir() / "appcache" / "librarycache"
    appids = {i.rsplit("_", 1)[-1] for i in skip_ids if i.startswith(f"{ID}_")}
    for manifest in _manifests():
        contents = manifest.read_text("utf-8")
        try:
            name, appid, stateflags = (
                _parse(contents, key) for key in ("name", "appid", "stateflags")
            )
            stateflags = int(stateflags)
        except ValueError:
            continue

        duplicate = appid in appids
        installed = stateflags & _INSTALLED_MASK

        if duplicate or not installed:
            continue

        game = Game(
            added=added,
            executable=f"{OPEN} steam://rungameid/{appid}",
            game_id=f"{ID}_{appid}",
            source=ID,
            name=name,
        )

        for path in itertools.chain.from_iterable(
            (librarycache / appid).rglob(filename) for filename in _CAPSULE_NAMES
        ):
            try:
                game.cover = Gdk.Texture.new_from_filename(str(path))
            except GLib.Error:
                continue
            else:
                break

        yield game
        appids.add(appid)


def _data_dir() -> Path:
    for path in _DATA_PATHS:
        if path.is_dir():
            return path

    raise FileNotFoundError


def _library_folders() -> Generator[Path]:
    return (
        steamapps
        for folder in re.findall(
            r'"path"\s+"(.*)"\n',
            (_data_dir() / "steamapps" / "libraryfolders.vdf").read_text("utf-8"),
            re.IGNORECASE,
        )
        if (steamapps := Path(folder) / "steamapps").is_dir()
    )


def _manifests() -> Generator[Path]:
    return (
        manifest
        for folder in _library_folders()
        for manifest in folder.glob("appmanifest_*.acf")
        if manifest.is_file()
    )


def _parse(manifest: str, key: str) -> str:
    match = re.search(rf'"{key}"\s+"(.*)"\n', manifest, re.IGNORECASE)
    if match and isinstance(group := match.group(1), str):
        return group

    raise ValueError
