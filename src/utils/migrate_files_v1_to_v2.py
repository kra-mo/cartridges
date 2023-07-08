# window.py
#
# Copyright 2023 Geoffrey Coulaud
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

import logging
from pathlib import Path
from shutil import copyfile
import os

from src import shared


def migrate_files_v1_to_v2():
    """
    Migrate user data from the v1.X locations to the latest location.

    Fix for commit 4a204442b5d8ba2e918f8c2605d72e483bf35efd
    where the windows directories for data, config and cache changed.
    """

    old_data_dir: Path = (
        Path(os.getenv("XDG_DATA_HOME"))
        if "XDG_DATA_HOME" in os.environ
        else Path.home() / ".local" / "share"
    )

    # Skip if there is no old dir
    # Skip if old == new
    # Skip if already migrated
    migrated_file = old_data_dir / ".migrated"
    if (
        not old_data_dir.is_dir()
        or str(old_data_dir) == str(shared.data_dir)
        or migrated_file.is_file()
    ):
        return

    logging.info("Migrating data dir %s", str(old_data_dir))

    # Migrate games if they don't exist in the current data dir.
    # If a game is migrated, its covers should be too.
    old_games_dir = old_data_dir / "games"
    old_covers_dir = old_data_dir / "covers"
    current_games_dir = shared.data_dir / "games"
    current_covers_dir = shared.data_dir / "covers"
    for game_file in old_games_dir.iterdir():
        # Ignore non game files
        if not game_file.is_file() or game_file.suffix != ".json":
            continue

        # Do nothing if already in games dir
        destination_game_file = current_games_dir / game_file.name
        if destination_game_file.exists():
            continue

        # Else, migrate the game
        copyfile(game_file, destination_game_file)
        logging.info("Copied %s -> %s", str(game_file), str(destination_game_file))

        # Migrate covers
        for suffix in (".tiff", ".gif"):
            cover_file = old_covers_dir / game_file.with_suffix(suffix).name
            if not cover_file.is_file():
                continue
            destination_cover_file = current_covers_dir / cover_file.name
            copyfile(cover_file, destination_cover_file)
            logging.info(
                "Copied %s -> %s", str(cover_file), str(destination_cover_file)
            )

    # Signal that this dir is migrated
    migrated_file.touch()
    logging.info("Migration done")
