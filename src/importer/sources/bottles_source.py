from pathlib import Path
from time import time

import yaml

from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)
from src.utils.decorators import (
    replaced_by_path,
    replaced_by_schema_key,
)


class BottlesSourceIterator(SourceIterator):
    source: "BottlesSource"

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games"""

        data = (self.source.location / "library.yml").read_text("utf-8")
        library: dict = yaml.safe_load(data)

        for entry in library.values():
            # Build game
            values = {
                "version": shared.SPEC_VERSION,
                "source": self.source.id,
                "added": int(time()),
                "name": entry["name"],
                "game_id": self.source.game_id_format.format(game_id=entry["id"]),
                "executable": self.source.executable_format.format(
                    bottle_name=entry["bottle"]["name"], game_name=entry["name"]
                ),
            }
            game = Game(values, allow_side_effects=False)

            # Get official cover path
            try:
                # This will not work if both Cartridges and Bottles are installed via Flatpak
                # as Cartridges can't access directories picked via Bottles' file picker portal
                bottles_location = Path(
                    yaml.safe_load(
                        (self.source.location / "data.yml").read_text("utf-8")
                    )["custom_bottles_path"]
                )
            except (FileNotFoundError, KeyError):
                bottles_location = self.source.location / "bottles"

            bottle_path = entry["bottle"]["path"]
            image_name = entry["thumbnail"].split(":")[1]
            image_path = bottles_location / bottle_path / "grids" / image_name
            additional_data = {"local_image_path": image_path}

            # Produce game
            yield (game, additional_data)


class BottlesSource(URLExecutableSource):
    """Generic Bottles source"""

    name = "Bottles"
    iterator_class = BottlesSourceIterator
    url_format = 'bottles:run/"{bottle_name}"/"{game_name}"'
    available_on = set(("linux",))

    @property
    @replaced_by_schema_key
    @replaced_by_path("~/.var/app/com.usebottles.bottles/data/bottles/")
    @replaced_by_path(shared.data_dir / "bottles")
    def location(self) -> Path:
        raise FileNotFoundError()
