from functools import cached_property
from sqlite3 import connect

from src.utils.save_cover import resize_cover, save_cover
from src.importer.source import Source, SourceIterator
from src.importer.decorators import replaced_by_schema_key, replaced_by_path


class LutrisSourceIterator(SourceIterator):
    ignore_steam_games = False  # TODO get that value

    db_connection = None
    db_cursor = None
    db_location = None
    db_request = None

    def __init__(self, ignore_steam_games):
        super().__init__()
        self.ignore_steam_games = ignore_steam_games
        self.db_connection = None
        self.db_cursor = None
        self.db_location = self.source.location / "pga.db"
        self.db_request = """
            SELECT
                id, name, slug, runner, hidden
            FROM
                'games'
            WHERE
                name IS NOT NULL
                AND slug IS NOT NULL
                AND configPath IS NOT NULL
                AND installed IS TRUE
            ;
        """

    def __next__(self):
        """Produce games. Behaviour depends on the state of the iterator."""

        # Get database contents iterator
        if self.state == self.States.DEFAULT:
            self.db_connection = connect(self.db_location)
            self.db_cursor = self.db_connection.execute(self.db_request)
            self.state = self.States.READY

        while True:
            # Get next DB value
            try:
                row = self.db_cursor.__next__()
            except StopIteration as e:
                self.db_connection.close()
                raise e

            # Ignore steam games if requested
            if row[3] == "steam" and self.ignore_steam_games:
                continue

            # Build basic game
            values = {
                "hidden": row[4],
                "name": row[1],
                "source": f"{self.source.id}_{row[3]}",
                "game_id": self.source.game_id_format.format(
                    game_id=row[2], game_internal_id=row[0]
                ),
                "executable": self.source.executable_format.format(game_id=row[2]),
                "developer": None,  # TODO get developer metadata on Lutris
            }

            # Save official image
            image_path = self.source.cache_location / "coverart" / f"{row[2]}.jpg"
            if image_path.exists():
                resized = resize_cover(self.source.win, image_path)
                save_cover(self.source.win, values["game_id"], resized)

            # TODO Save SGDB

            return values


class LutrisSource(Source):
    name = "Lutris"
    executable_format = "xdg-open lutris:rungameid/{game_id}"
    location = None
    cache_location = None

    @property
    def game_id_format(self):
        return super().game_id_format + "_{game_internal_id}"

    def __init__(self, win):
        super().__init__(win)

    def __iter__(self):
        return LutrisSourceIterator(source=self)


class LutrisNativeSource(LutrisSource):
    """Class representing an installation of Lutris using native packaging"""

    variant = "native"

    @cached_property
    @replaced_by_schema_key("lutris-location")
    @replaced_by_path("~/.local/share/lutris/")
    def location(self):
        raise FileNotFoundError()

    @cached_property
    @replaced_by_schema_key("lutris-cache-location")
    @replaced_by_path("~/.local/share/lutris/covers")
    def cache_location(self):
        raise FileNotFoundError()


class LutrisFlatpakSource(LutrisSource):
    """Class representing an installation of Lutris using flatpak"""

    variant = "flatpak"

    @cached_property
    @replaced_by_schema_key("lutris-flatpak-location")
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris")
    def location(self):
        raise FileNotFoundError()

    @cached_property
    @replaced_by_schema_key("lutris-flatpak-cache-location")
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris/covers")
    def cache_location(self):
        raise FileNotFoundError()
