# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2023 Geoffrey Coulaud
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import itertools
import logging
import re
import struct
import time
from collections.abc import Generator, Iterable, Sequence
from contextlib import suppress
from gettext import gettext as _
from os import SEEK_CUR
from pathlib import Path
from typing import Any, BinaryIO, NamedTuple, Self, cast

from gi.repository import Gdk, GLib

from cartridges.games import Game

from . import APPLICATION_SUPPORT, DATA, FLATPAK, OPEN, PROGRAM_FILES_X86

ID, NAME = "steam", _("Steam")

_DATA_PATHS = (
    Path.home() / ".steam" / "steam",
    DATA / "Steam",
    FLATPAK / "com.valvesoftware.Steam" / "data" / "Steam",
    PROGRAM_FILES_X86 / "Steam",
    APPLICATION_SUPPORT / "Steam",
)

_MANIFEST_INSTALLED_MASK = 4
_RELEVANT_TYPES = "game", "demo", "mod"
_CAPSULE_NAMES = "library_600x900.jpg", "library_capsule.jpg", "capsule_231x87.jpg"
_CAPSULE_KEYS = ("library_assets_full", "library_capsule", "image"), ("small_capsule",)
_APPINFO_MAGIC = b")DV\x07"
_VDF_TYPES = {
    b"\x00": lambda fp, table: dict(_load_binary_vdf(fp, table)),
    b"\x01": lambda fp, _: _read_string(fp),
    b"\x02": lambda fp, _: struct.unpack("<i", fp.read(4))[0],
    b"\x03": lambda fp, _: struct.unpack("<f", fp.read(4))[0],
    b"\x04": lambda fp, _: struct.unpack("<i", fp.read(4))[0],
    b"\x05": lambda fp, _: _read_string(fp, wide=True),
    b"\x06": lambda fp, _: struct.unpack("<i", fp.read(4))[0],
    b"\x07": lambda fp, _: struct.unpack("<Q", fp.read(8))[0],
    b"\x0a": lambda fp, _: struct.unpack("<q", fp.read(8))[0],
}

_logger = logging.getLogger(__name__)


class _App(NamedTuple):
    name: str
    appid: str
    stateflags: str | None = None
    lastplayed: str | None = None

    @classmethod
    def from_manifest(cls, path: Path) -> Self:
        data = path.read_text("utf-8", "replace")
        try:
            return cls(
                *(
                    m.group(1)
                    if (m := re.search(rf'"{field}"\s+"(.*?)"\n', data, re.IGNORECASE))
                    else cls._field_defaults[field]
                    for field in cls._fields
                )
            )
        except KeyError as e:
            raise ValueError from e


class _AppInfo(NamedTuple):
    type: str | None = None
    developer: str | None = None
    capsule: str | None = None

    @classmethod
    def from_vdf(cls, fp: BinaryIO, key_table: Sequence[str]) -> Self:
        try:
            common = dict(_load_binary_vdf(fp, key_table))["appinfo"]["common"]
        except (SyntaxError, TypeError, KeyError):
            return cls()

        try:
            developer = ", ".join(
                association["name"]
                for association in common["associations"].values()
                if association.get("type") == "developer"
            )
        except (TypeError, AttributeError, KeyError):
            developer = None

        capsule = None
        for keys in _CAPSULE_KEYS:
            value = common
            with suppress(AttributeError, KeyError):
                for key in keys:
                    value = value.get(key)

                capsule = value.get("english", value.popitem()[1])
                break

        return cls(common.get("type"), developer, capsule)


def get_games(*, skip_ids: Iterable[str]) -> Generator[Game]:
    """Installed Steam games."""
    added = int(time.time())

    librarycache = _data_dir() / "appcache" / "librarycache"
    with (_data_dir() / "appcache" / "appinfo.vdf").open("rb") as fp:
        appinfo = dict(_parse_appinfo_vdf(fp))

    appids = {i.rsplit("_", 1)[-1] for i in skip_ids if i.startswith(f"{ID}_")}
    for manifest in _manifests():
        try:
            app = _App.from_manifest(manifest)
        except ValueError:
            continue

        duplicate = app.appid in appids
        installed = (
            int(app.stateflags) & _MANIFEST_INSTALLED_MASK
            if app.stateflags and app.stateflags.isdigit()
            else True
        )

        if duplicate or not installed:
            continue

        info = appinfo.get(app.appid)
        if info and info.type and (info.type.lower() not in _RELEVANT_TYPES):
            continue

        appids.add(app.appid)
        yield Game(
            added=added,
            executable=f"{OPEN} steam://rungameid/{app.appid}",
            game_id=f"{ID}_{app.appid}",
            source=ID,
            last_played=int(app.lastplayed)
            if app.lastplayed and app.lastplayed.isdigit()
            else 0,
            name=app.name,
            developer=info.developer if info else None,
            cover=_find_cover(librarycache / app.appid, info.capsule if info else None),
        )


def _data_dir() -> Path:
    for path in _DATA_PATHS:
        if path.is_dir():
            return path

    raise FileNotFoundError


def _library_folders() -> Generator[Path]:
    vdf = _data_dir() / "steamapps" / "libraryfolders.vdf"
    return (
        steamapps
        for folder in re.findall(
            r'"path"\s+"(.*?)"\n',
            vdf.read_text("utf-8", "replace"),
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


def _parse_appinfo_vdf(fp: BinaryIO) -> Generator[tuple[str, _AppInfo]]:
    if fp.read(4) != _APPINFO_MAGIC:
        _logger.warning("Magic number mismatch, parsing appinfo.vdf will likely fail.")

    fp.seek(4, SEEK_CUR)
    table_offset = struct.unpack("q", fp.read(8))[0]
    offset = fp.tell()
    fp.seek(table_offset)
    table = tuple(_read_string(fp) for _ in range(struct.unpack("<I", fp.read(4))[0]))

    fp.seek(offset)
    while appid := struct.unpack("<I", fp.read(4))[0]:
        fp.seek(64, SEEK_CUR)
        yield str(appid), _AppInfo.from_vdf(fp, table)


def _load_binary_vdf(
    fp: BinaryIO, key_table: Sequence[str]
) -> Generator[tuple[str, Any]]:
    for type_ in iter(lambda: fp.read(1), b"\x08"):
        try:
            key = key_table[cast(int, struct.unpack("<i", fp.read(4))[0])]
            yield key, _VDF_TYPES[type_](fp, key_table)
        except (IndexError, KeyError) as e:
            raise SyntaxError from e


def _read_string(fp: BinaryIO, *, wide: bool = False) -> str:
    size, encoding = (2, "utf-16") if wide else (1, "utf-8")

    string = b""
    for char in iter(lambda: fp.read(size), b"\x00" * size):
        if char == b"":
            raise SyntaxError

        string += char

    return string.decode(encoding, "replace")


def _find_cover(path: Path, capsule: str | None = None) -> Gdk.Texture | None:
    paths = [*itertools.chain.from_iterable(path.rglob(p) for p in _CAPSULE_NAMES)]
    if capsule:
        paths.insert(0, path / capsule)

    for filename in map(str, paths):
        try:
            return Gdk.Texture.new_from_filename(filename)
        except GLib.Error:
            continue

    return None
