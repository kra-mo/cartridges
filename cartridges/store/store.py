# store.py
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
from typing import Any, Generator, MutableMapping, Optional

from cartridges import shared
from cartridges.game import Game
from cartridges.store.managers.manager import Manager
from cartridges.store.pipeline import Pipeline


class Store:
    """Class in charge of handling games being added to the app."""

    managers: dict[type[Manager], Manager]
    pipeline_managers: set[Manager]
    pipelines: dict[str, Pipeline]
    source_games: MutableMapping[str, MutableMapping[str, Game]]
    new_game_ids: set[str]
    duplicate_game_ids: set[str]

    def __init__(self) -> None:
        self.managers = {}
        self.pipeline_managers = set()
        self.pipelines = {}
        self.source_games = {}
        self.new_game_ids = set()
        self.duplicate_game_ids = set()

    def __contains__(self, obj: object) -> bool:
        """Check if the game is present in the store with the `in` keyword"""
        if not isinstance(obj, Game):
            return False
        if not (source_mapping := self.source_games.get(obj.base_source)):
            return False
        return obj.game_id in source_mapping

    def __iter__(self) -> Generator[Game, None, None]:
        """Iterate through the games in the store with `for ... in`"""
        for _source_id, games_mapping in self.source_games.items():
            for _game_id, game in games_mapping.items():
                yield game

    def __len__(self) -> int:
        """Get the number of games in the store with the `len` builtin"""
        return sum(len(source_mapping) for source_mapping in self.source_games.values())

    def __getitem__(self, game_id: str) -> Game:
        """Get a game by its id with `store["game_id_goes_here"]`"""
        for game in iter(self):
            if game.game_id == game_id:
                return game
        raise KeyError("Game not found in store")

    def get(self, game_id: str, default: Any = None) -> Game | Any:
        """Get a game by its ID, with a fallback if not found"""
        try:
            game = self[game_id]
            return game
        except KeyError:
            return default

    def add_manager(self, manager: Manager, in_pipeline: bool = True) -> None:
        """Add a manager to the store"""
        manager_type = type(manager)
        self.managers[manager_type] = manager
        self.toggle_manager_in_pipelines(manager_type, in_pipeline)

    def toggle_manager_in_pipelines(
        self, manager_type: type[Manager], enable: bool
    ) -> None:
        """Change if a manager should run in new pipelines"""
        if enable:
            self.pipeline_managers.add(self.managers[manager_type])
        else:
            self.pipeline_managers.discard(self.managers[manager_type])

    def cleanup_game(self, game: Game) -> None:
        """Remove a game's files, dismiss any loose toasts"""
        for path in (
            shared.games_dir / f"{game.game_id}.json",
            shared.covers_dir / f"{game.game_id}.tiff",
            shared.covers_dir / f"{game.game_id}.gif",
        ):
            path.unlink(missing_ok=True)

        # TODO: don't run this if the state is startup
        for undo in ("remove", "hide"):
            try:
                shared.win.toasts[(game, undo)].dismiss()
                shared.win.toasts.pop((game, undo))
            except KeyError:
                pass

    def add_game(
        self, game: Game, additional_data: dict, run_pipeline: bool = True
    ) -> Optional[Pipeline]:
        """Add a game to the app"""

        # Ignore games from a newer spec version
        if game.version > shared.SPEC_VERSION:
            return None

        # Scanned game is already removed, just clean it up
        if game.removed:
            self.cleanup_game(game)
            return None

        # Handle game duplicates
        stored_game = self.get(game.game_id)
        if not stored_game:
            # New game, do as normal
            logging.debug("New store game %s (%s)", game.name, game.game_id)
            self.new_game_ids.add(game.game_id)
        elif stored_game.removed:
            # Will replace a removed game, cleanup its remains
            logging.debug(
                "New store game %s (%s) (replacing a removed one)",
                game.name,
                game.game_id,
            )
            self.cleanup_game(stored_game)
            self.new_game_ids.add(game.game_id)
        else:
            # Duplicate game, ignore it
            logging.debug("Duplicate store game %s (%s)", game.name, game.game_id)
            self.duplicate_game_ids.add(game.game_id)
            return None

        # Connect signals
        for manager in self.managers.values():
            for signal in manager.signals:
                game.connect(signal, manager.run)

        # Add the game to the store
        if not game.base_source in self.source_games:
            self.source_games[game.base_source] = {}
        self.source_games[game.base_source][game.game_id] = game

        # Run the pipeline for the game
        if not run_pipeline:
            return None
        pipeline = Pipeline(game, additional_data, self.pipeline_managers)
        self.pipelines[game.game_id] = pipeline
        pipeline.advance()
        return pipeline
