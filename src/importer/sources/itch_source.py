from sqlite3 import connect
from pathlib import Path
from time import time
from typing import Optional, Generator

from src import shared
from src.utils.decorators import replaced_by_env_path, replaced_by_path
from src.game import Game
from src.importer.sources.source import (
    Source,
    SourceIterator,
    LinuxSource,
    WindowsSource,
)


class ItchSourceIterator(SourceIterator):
    source: "ItchSource"

    def generator_builder(self) -> Generator[Optional[Game], None, None]:
        """Generator method producing games"""

        # Query the database
        db_request = """
        SELECT
            games.id,
            games.title,
            games.cover_url,
            games.still_cover_url,
            caves.id
        FROM
            'caves'
        INNER JOIN
            'games'
        ON
            caves.game_id = games.id
        ;
        """
        connection = connect(self.source.location / "db" / "butler.db")
        cursor = connection.execute(db_request)

        # Create games from the db results
        for row in cursor:
            values = {
                "version": shared.SPEC_VERSION,
                "added": int(time()),
                "source": self.source.id,
                "game_id": self.source.game_id_format.format(game_id=row[0]),
                "executable": self.source.executable_format.format(cave_id=row[4]),
            }
            yield Game(values, allow_side_effects=False)

            # TODO pass image URIs to the pipeline somehow
            # - Add a reserved field to the Game object
            # - Reconstruct those from the pipeline (we already have them)
            # - Pass game and additional data to the pipeline separately (requires deep changes)


class ItchSource(Source):
    name = "Itch"
    location_key = "itch-location"

    def __iter__(self) -> SourceIterator:
        return ItchSourceIterator(self)


class ItchLinuxSource(ItchSource, LinuxSource):
    variant = "linux"
    executable_format = "xdg-open itch://caves/{cave_id}/launch"

    @ItchSource.replaced_by_schema_key()
    @replaced_by_path("~/.var/app/io.itch.itch/config/itch/")
    @replaced_by_env_path("XDG_DATA_HOME", "itch/")
    @replaced_by_path("~/.config/itch")
    def location(self) -> Path:
        raise FileNotFoundError()


class ItchWindowsSource(ItchSource, WindowsSource):
    variant = "windows"
    executable_format = "start itch://caves/{cave_id}/launch"

    @ItchSource.replaced_by_schema_key()
    @replaced_by_env_path("appdata", "itch/")
    def location(self) -> Path:
        raise FileNotFoundError()
