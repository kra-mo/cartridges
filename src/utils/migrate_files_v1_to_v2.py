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

import json
import logging
import os
from pathlib import Path
from shutil import copyfile

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
    old_cartridges_data_dir = old_data_dir / "cartridges"

    # Skip if there is no old dir
    # Skip if old == current
    # Skip if already migrated
    migrated_file = old_cartridges_data_dir / ".migrated"
    if (
        not old_data_dir.is_dir()
        or str(old_data_dir) == str(shared.data_dir)
        or migrated_file.is_file()
    ):
        return

    logging.info("Migrating data dir %s", str(old_data_dir))

    # Create the current data dir if needed
    if not shared.data_dir.is_dir():
        shared.data_dir.mkdir(parents=True)

    old_games_dir = old_cartridges_data_dir / "games"
    old_covers_dir = old_cartridges_data_dir / "covers"

    old_games = set(old_games_dir.glob("*.json"))
    old_imported_games = set(
        filter(lambda path: path.name.startswith("imported_"), old_games)
    )
    old_other_games = old_games - old_imported_games

    # Discover current imported games
    imported_game_number = 0
    imported_execs = set()
    for game in shared.games_dir.glob("imported_*.json"):
        try:
            game_data = json.load(game.open("r"))
        except (OSError, json.JSONDecodeError):
            continue
        number = int(game_data["game_id"].replace("imported_", ""))
        imported_game_number = max(number, imported_game_number)
        imported_execs.add(game_data["executable"])

    # Migrate imported game files
    for game in old_imported_games:
        try:
            game_data = json.load(game.open("r"))
        except (OSError, json.JSONDecodeError):
            continue

        # Don't migrate if there's a game with the same exec
        if game_data["executable"] in imported_execs:
            continue

        # Migrate with updated index
        imported_game_number += 1
        game_id = f"imported_{imported_game_number}"
        game_data["game_id"] = game_id
        destination_game_file = shared.games_dir / f"{game_id}.json"
        json.dump(game_data, destination_game_file.open("w"))

    # Migrate all other games
    for game in old_other_games:
        # Do nothing if already in games dir
        destination_game_file = shared.games_dir / game.name
        if destination_game_file.exists():
            continue

        # Else, migrate the game
        copyfile(game, destination_game_file)
        logging.info("Copied %s -> %s", str(game), str(destination_game_file))

        # Migrate covers
        for suffix in (".tiff", ".gif"):
            cover_file = old_covers_dir / game.with_suffix(suffix).name
            if not cover_file.is_file():
                continue
            destination_cover_file = shared.covers_dir / cover_file.name
            copyfile(cover_file, destination_cover_file)
            logging.info(
                "Copied %s -> %s", str(cover_file), str(destination_cover_file)
            )

    # Signal that this dir is migrated
    migrated_file.touch()
    logging.info("Migration done")
