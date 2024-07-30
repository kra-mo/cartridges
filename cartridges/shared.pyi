# shared.pyi
#
# Copyright 2024 kramo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path
from typing import Optional

from gi.repository import Gio

from cartridges.importer.importer import Importer
from cartridges.store.store import Store
from cartridges.window import CartridgesWindow


class AppState:
    DEFAULT: int
    LOAD_FROM_DISK: int
    IMPORT: int
    REMOVE_ALL_GAMES: int
    UNDO_REMOVE_ALL_GAMES: int


APP_ID: str
VERSION: str
PREFIX: str
PROFILE: str
TIFF_COMPRESSION: str
SPEC_VERSION: float

schema: Gio.Settings
state_schema: Gio.Settings

home: Path

data_dir: Path
host_data_dir: Path

config_dir: Path
host_config_dir: Path

cache_dir: Path
host_cache_dir: Path

flatpak_dir: Path

games_dir: Path
covers_dir: Path

appdata_dir: Path
local_appdata_dir: Path
programfiles32_dir: Path

app_support_dir: Path


scale_factor: int
image_size: int

win: Optional[CartridgesWindow]
importer: Optional[Importer]
import_time: Optional[int]
store = Optional[Store]
log_files: list[Path]
