from shutil import rmtree
from sqlite3 import connect
from time import time

from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)
from src.utils.decorators import replaced_by_path, replaced_by_schema_key
from src.utils.sqlite import copy_db


class LutrisSourceIterator(SourceIterator):
    source: "LutrisSource"

    def generator_builder(self) -> SourceIterationResult:
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
        db_path = copy_db(self.source.location / "pga.db")
        connection = connect(db_path)
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
            }
            game = Game(values, allow_side_effects=False)

            # Get official image path
            image_path = self.source.location / "covers" / "coverart" / f"{row[2]}.jpg"
            additional_data = {"local_image_path": image_path}

            # Produce game
            yield (game, additional_data)

        # Cleanup
        rmtree(str(db_path.parent))


class LutrisSource(URLExecutableSource):
    """Generic lutris source"""

    name = "Lutris"
    iterator_class = LutrisSourceIterator
    url_format = "lutris:rungameid/{game_id}"
    available_on = set(("linux",))

    @property
    def game_id_format(self):
        return super().game_id_format + "_{game_internal_id}"

    @property
    @replaced_by_schema_key
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris/")
    @replaced_by_path("~/.local/share/lutris/")
    def location(self):
        raise FileNotFoundError()
