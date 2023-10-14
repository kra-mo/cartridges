# migrate_files_v1_to_v2.py
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
from pathlib import Path

from cartridges import shared

old_data_dir = shared.home / ".local" / "share"
old_cartridges_data_dir = old_data_dir / "cartridges"
migrated_file_path = old_cartridges_data_dir / ".migrated"
old_games_dir = old_cartridges_data_dir / "games"
old_covers_dir = old_cartridges_data_dir / "covers"


def migrate_game_covers(game_path: Path) -> None:
    """Migrate a game covers from a source game path to the current dir"""
    for suffix in (".tiff", ".gif"):
        cover_path = old_covers_dir / game_path.with_suffix(suffix).name
        if not cover_path.is_file():
            continue
        destination_cover_path = shared.covers_dir / cover_path.name
        logging.info("Moving %s -> %s", str(cover_path), str(destination_cover_path))
        cover_path.rename(destination_cover_path)


def migrate_files_v1_to_v2() -> None:
    """
    Migrate user data from the v1.X locations to the latest location.

    Fix for commit 4a204442b5d8ba2e918f8c2605d72e483bf35efd
    where the windows directories for data, config and cache changed.
    """

    # Skip if there is no old dir
    # Skip if old == current
    # Skip if already migrated
    if (
        not old_data_dir.is_dir()
        or str(old_data_dir) == str(shared.data_dir)
        or migrated_file_path.is_file()
    ):
        return

    logging.info("Migrating data dir %s", str(old_data_dir))

    # Create new directories
    shared.games_dir.mkdir(parents=True, exist_ok=True)
    shared.covers_dir.mkdir(parents=True, exist_ok=True)

    old_game_paths = set(old_games_dir.glob("*.json"))
    old_imported_game_paths = set(
        filter(lambda path: path.name.startswith("imported_"), old_game_paths)
    )
    old_other_game_paths = old_game_paths - old_imported_game_paths

    # Discover current imported games
    imported_game_number = 0
    imported_execs = set()
    for game_path in shared.games_dir.glob("imported_*.json"):
        try:
            game_data = json.load(game_path.open("r", encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        number = int(game_data["game_id"].replace("imported_", ""))
        imported_game_number = max(number, imported_game_number)
        imported_execs.add(game_data["executable"])

    # Migrate imported game files
    for game_path in old_imported_game_paths:
        try:
            game_data = json.load(game_path.open("r", encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        # Don't migrate if there's a game with the same exec
        if game_data["executable"] in imported_execs:
            continue

        # Migrate with updated index
        imported_game_number += 1
        game_id = f"imported_{imported_game_number}"
        game_data["game_id"] = game_id
        destination_game_path = shared.games_dir / f"{game_id}.json"
        logging.info(
            "Moving (updated id) %s -> %s", str(game_path), str(destination_game_path)
        )
        json.dump(
            game_data,
            destination_game_path.open("w", encoding="utf-8"),
            indent=4,
            sort_keys=True,
        )
        game_path.unlink()
        migrate_game_covers(game_path)

    # Migrate all other games
    for game_path in old_other_game_paths:
        # Do nothing if already in games dir
        destination_game_path = shared.games_dir / game_path.name
        if destination_game_path.exists():
            continue

        # Else, migrate the game
        logging.info("Moving %s -> %s", str(game_path), str(destination_game_path))
        game_path.rename(destination_game_path)
        migrate_game_covers(game_path)

    # Signal that this dir is migrated
    migrated_file_path.touch()
    logging.info("Migration done")
