from sqlite3 import connect
from time import time
from typing import Optional, Generator

from src import shared
from src.game import Game
from src.importer.sources.source import LinuxSource, Source, SourceIterator
from src.utils.decorators import replaced_by_path, replaced_by_schema_key
from src.utils.save_cover import resize_cover, save_cover


class LutrisSourceIterator(SourceIterator):
    source: "LutrisSource"

    def generator_builder(self) -> Optional[Game]:
        """Generator method producing games"""

        # Query the database
        request = """
            SELECT id, name, slug, runner, hidden
            FROM 'games'
            WHERE
                name IS NOT NULL
                AND slug IS NOT NULL
                AND configPath IS NOT NULL
                AND installed
                AND (runner IS NOT "steam" OR :import_steam)
            ;
        """
        params = {"import_steam": shared.schema.get_boolean("lutris-import-steam")}
        connection = connect(self.source.location / "pga.db")
        cursor = connection.execute(request, params)

        # Create games from the DB results
        for row in cursor:
            # Create game
            values = {
                "version": shared.SPEC_VERSION,
                "added": int(time()),
                "hidden": row[4],
                "name": row[1],
                "source": f"{self.source.id}_{row[3]}",
                "game_id": self.source.game_id_format.format(
                    game_id=row[2], game_internal_id=row[0]
                ),
                "executable": self.source.executable_format.format(game_id=row[2]),
                "developer": None,  # TODO get developer metadata on Lutris
            }
            game = Game(values, allow_side_effects=False)

            # Save official image
            image_path = self.source.location / "covers" / "coverart" / f"{row[2]}.jpg"
            if image_path.exists():
                save_cover(values["game_id"], resize_cover(image_path))

            # Produce game
            yield game


class LutrisSource(Source):
    """Generic lutris source"""

    name = "Lutris"

    @property
    def game_id_format(self):
        return super().game_id_format + "_{game_internal_id}"

    def __iter__(self):
        return LutrisSourceIterator(source=self)


class LutrisLinuxSource(LutrisSource, LinuxSource):
    variant = "linux"
    executable_format = "xdg-open lutris:rungameid/{game_id}"

    @property
    @replaced_by_schema_key("lutris-location")
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris/")
    @replaced_by_path("~/.local/share/lutris/")
    def location(self):
        raise FileNotFoundError()
