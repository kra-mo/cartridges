from pathlib import Path
from time import time
from typing import Optional, Generator

import yaml

from src import shared
from src.game import Game
from src.importer.sources.source import LinuxSource, Source, SourceIterator
from src.utils.decorators import replaced_by_env_path, replaced_by_path
from src.utils.save_cover import resize_cover, save_cover


class BottlesSourceIterator(SourceIterator):
    source: "BottlesSource"

    def generator_builder(self) -> Generator[Optional[Game], None, None]:
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


class BottlesSource(Source):
    """Generic Bottles source"""

    name = "Bottles"
    location_key = "bottles-location"

    def __iter__(self) -> SourceIterator:
        return BottlesSourceIterator(self)


class BottlesLinuxSource(BottlesSource, LinuxSource):
    variant = "linux"
    executable_format = 'xdg-open bottles:run/"{bottle_name}"/"{game_name}"'

    @property
    @BottlesSource.replaced_by_schema_key()
    @replaced_by_path("~/.var/app/com.usebottles.bottles/data/bottles/")
    @replaced_by_env_path("XDG_DATA_HOME", "bottles/")
    @replaced_by_path("~/.local/share/bottles/")
    def location(self) -> Path:
        raise FileNotFoundError()
