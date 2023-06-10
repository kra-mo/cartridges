import json
import logging
from json import JSONDecodeError
from pathlib import Path
from time import time
from typing import Generator

from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.importer.sources.source import Source, SourceIterationResult, SourceIterator
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)


class LegendarySourceIterator(SourceIterator):
    source: "LegendarySource"

    def game_from_library_entry(self, entry: dict) -> SourceIterationResult:
        # Skip non-games
        if entry["is_dlc"]:
            return None

        # Build game
        app_name = entry["app_name"]
        values = {
            "version": shared.SPEC_VERSION,
            "added": int(time()),
            "source": self.source.id,
            "name": entry["title"],
            "game_id": self.source.game_id_format.format(game_id=app_name),
            "executable": self.source.executable_format.format(app_name=app_name),
        }
        data = {}

        # Get additional metadata from file (optional)
        metadata_file = self.source.location / "metadata" / f"{app_name}.json"
        try:
            metadata = json.load(metadata_file.open())
            values["developer"] = metadata["metadata"]["developer"]
            for image_entry in metadata["metadata"]["keyImages"]:
                if image_entry["type"] == "DieselGameBoxTall":
                    data["online_cover_url"] = image_entry["url"]
                    break
        except (JSONDecodeError, OSError, KeyError):
            pass

        game = Game(values, allow_side_effects=False)
        return (game, data)

    def generator_builder(self) -> Generator[SourceIterationResult, None, None]:
        # Open library
        file = self.source.location / "installed.json"
        try:
            library: dict = json.load(file.open())
        except (JSONDecodeError, OSError):
            logging.warning("Couldn't open Legendary file: %s", str(file))
            return
        # Generate games from library
        for entry in library.values():
            try:
                result = self.game_from_library_entry(entry)
            except KeyError as error:
                # Skip invalid games
                logging.warning(
                    "Invalid Legendary game skipped in %s", str(file), exc_info=error
                )
                continue
            yield result


class LegendarySource(Source):
    name = "Legendary"
    executable_format = "legendary launch {app_name}"
    iterator_class = LegendarySourceIterator
    available_on = set(("linux", "win32"))

    @property
    @replaced_by_schema_key
    @replaced_by_env_path("XDG_CONFIG_HOME", "legendary/")
    @replaced_by_path("~/.config/legendary/")
    @replaced_by_path("~\\.config\\legendary\\")
    def location(self) -> Path:
        raise FileNotFoundError()
