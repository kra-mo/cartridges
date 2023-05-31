from abc import abstractmethod
from functools import lru_cache
from pathlib import Path
from sqlite3 import connect
from time import time

from src import shared
from src.game import Game
from src.importer.sources.source import Source, SourceIterator
from src.utils.decorators import replaced_by_path, replaced_by_schema_key
from src.utils.save_cover import resize_cover, save_cover


class LutrisSourceIterator(SourceIterator):
    import_steam = False
    db_connection = None
    db_cursor = None
    db_location = None
    db_games_request = """
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
    db_request_params = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.import_steam = shared.schema.get_boolean("lutris-import-steam")
        self.db_location = self.source.location / "pga.db"
        self.db_connection = connect(self.db_location)
        self.db_request_params = {"import_steam": self.import_steam}
        self.db_cursor = self.db_connection.execute(
            self.db_games_request, self.db_request_params
        )

    def __next__(self):
        """Produce games"""

        row = None
        try:
            row = self.db_cursor.__next__()
        except StopIteration as error:
            self.db_connection.close()
            raise error

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

        return game


class LutrisSource(Source):
    """Generic lutris source"""

    name = "Lutris"
    executable_format = "xdg-open lutris:rungameid/{game_id}"

    @property
    @abstractmethod
    def location(self) -> Path:
        pass

    @property
    def game_id_format(self):
        return super().game_id_format + "_{game_internal_id}"

    @property
    def is_installed(self):
        # pylint: disable=pointless-statement
        try:
            self.location
        except FileNotFoundError:
            return False
        return True

    def __iter__(self):
        return LutrisSourceIterator(source=self)


class LutrisNativeSource(LutrisSource):
    variant = "native"

    @property
    @replaced_by_schema_key("lutris-location")
    @replaced_by_path("~/.local/share/lutris/")
    def location(self):
        raise FileNotFoundError()


class LutrisFlatpakSource(LutrisSource):
    variant = "flatpak"

    @property
    @replaced_by_schema_key("lutris-flatpak-location")
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris/")
    def location(self):
        raise FileNotFoundError()
