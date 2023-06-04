from pathlib import Path
from time import time
from typing import Generator, Optional

import yaml

from src import shared
from src.game import Game
from src.importer.sources.source import LinuxSource, Source, SourceIterator
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)
from src.utils.save_cover import resize_cover, save_cover


class BottlesSourceIterator(SourceIterator):
    source: "BottlesSource"
    generator: Generator = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.generator = self.generator_builder()

    def generator_builder(self) -> Optional[Game]:
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

            # Save official cover
            bottle_path = entry["bottle"]["path"]
            image_name = entry["thumbnail"].split(":")[1]
            image_path = (
                self.source.location / "bottles" / bottle_path / "grids" / image_name
            )
            if image_path.is_file():
                save_cover(values["game_id"], resize_cover(image_path))

            # Produce game
            yield game

    def __next__(self) -> Optional[Game]:
        try:
            game = next(self.generator)
        except StopIteration:
            raise
        return game


class BottlesSource(Source):
    """Generic Bottles source"""

    name = "Bottles"

    def __iter__(self) -> SourceIterator:
        return BottlesSourceIterator(self)


class BottlesLinuxSource(BottlesSource, LinuxSource):
    variant = "linux"
    executable_format = 'xdg-open bottles:run/"{bottle_name}"/"{game_name}"'

    @property
    @replaced_by_schema_key("bottles-location")
    @replaced_by_path("~/.var/app/com.usebottles.bottles/data/bottles/")
    @replaced_by_env_path("XDG_DATA_HOME", "bottles/")
    @replaced_by_path("~/.local/share/bottles/")
    def location(self) -> Path:
        raise FileNotFoundError()
