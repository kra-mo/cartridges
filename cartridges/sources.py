# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import itertools
import os
import re
import sys
import time
from collections.abc import Generator, Iterable
from pathlib import Path
from typing import Protocol

from gi.repository import Gdk, GLib

from cartridges.games import Game

DATA = Path(GLib.get_user_data_dir())
FLATPAK = Path.home() / ".var" / "app"
PROGRAM_FILES_X86 = Path(os.getenv("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
APPLICATION_SUPPORT = Path.home() / "Library" / "Application Support"

OPEN = (
    "open"
    if sys.platform.startswith("darwin")
    else "start"
    if sys.platform.startswith("win32")
    else "xdg-open"
)


class Source(Protocol):
    """A source of games to import."""

    ID: str

    def get_games(self, *, skip_ids: Iterable[str]) -> Generator[Game]:
        """Installed games, except those in `skip_ids`."""
        ...


class SteamSource:
    """A source for the Valve's Steam."""

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

    @property
    def _data(self) -> Path:
        for path in self._DATA_PATHS:
            if path.is_dir():
                return path

        raise FileNotFoundError

    @property
    def _library_folders(self) -> Generator[Path]:
        return (
            steamapps
            for folder in re.findall(
                r'"path"\s+"(.*)"\n',
                (self._data / "steamapps" / "libraryfolders.vdf").read_text("utf-8"),
                re.IGNORECASE,
            )
            if (steamapps := Path(folder) / "steamapps").is_dir()
        )

    @property
    def _manifests(self) -> Generator[Path]:
        return (
            manifest
            for folder in self._library_folders
            for manifest in folder.glob("appmanifest_*.acf")
            if manifest.is_file()
        )

    def get_games(self, *, skip_ids: Iterable[str]) -> Generator[Game]:
        """Installed Steam games."""
        added = int(time.time())
        librarycache = self._data / "appcache" / "librarycache"
        appids = {i.rsplit("_", 1)[-1] for i in skip_ids if i.startswith(f"{self.ID}_")}
        for manifest in self._manifests:
            contents = manifest.read_text("utf-8")
            try:
                name, appid, stateflags = (
                    self._parse(contents, key)
                    for key in ("name", "appid", "stateflags")
                )
                stateflags = int(stateflags)
            except ValueError:
                continue

            duplicate = appid in appids
            installed = stateflags & self._INSTALLED_MASK

            if duplicate or not installed:
                continue

            game = Game(
                added=added,
                executable=f"{OPEN} steam://rungameid/{appid}",
                game_id=f"{self.ID}_{appid}",
                source=self.ID,
                name=name,
            )

            for path in itertools.chain.from_iterable(
                (librarycache / appid).rglob(filename)
                for filename in self._CAPSULE_NAMES
            ):
                try:
                    game.cover = Gdk.Texture.new_from_filename(str(path))
                except GLib.Error:
                    continue
                else:
                    break

            yield game
            appids.add(appid)

    @staticmethod
    def _parse(manifest: str, key: str) -> str:
        match = re.search(rf'"{key}"\s+"(.*)"\n', manifest, re.IGNORECASE)
        if match and isinstance(group := match.group(1), str):
            return group

        raise ValueError
