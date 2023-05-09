from functools import cache
from sqlite3 import connect
from time import time

from .decorators import replaced_by_path, replaced_by_schema_key
from .game import Game
from .save_cover import resize_cover, save_cover
from .source import Source, SourceIterator


class LutrisSourceIterator(SourceIterator):
    import_steam = False
    db_connection = None
    db_cursor = None
    db_location = None
    db_len_request = """
        SELECT count(*)
        FROM 'games'
        WHERE
            name IS NOT NULL
            AND slug IS NOT NULL
            AND configPath IS NOT NULL
            AND installed
            AND (runner IS NOT "steam" OR :import_steam)
        ;
    """
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
        self.import_steam = self.source.win.schema.get_boolean("lutris-import-steam")
        self.db_location = self.source.location / "pga.db"
        self.db_connection = connect(self.db_location)
        self.db_request_params = {"import_steam": self.import_steam}
        self.__len__()  # Init iterator length
        self.db_cursor = self.db_connection.execute(
            self.db_games_request, self.db_request_params
        )

    @cache
    def __len__(self):
        cursor = self.db_connection.execute(self.db_len_request, self.db_request_params)
        return cursor.fetchone()[0]

    def __next__(self):
        """Produce games. Behaviour depends on the state of the iterator."""
        # TODO decouple game creation from the window object

        row = None
        try:
            row = self.db_cursor.__next__()
        except StopIteration as e:
            self.db_connection.close()
            raise e

        # Create game
        values = {
            "added": int(time()),
            "last_played": 0,
            "hidden": row[4],
            "name": row[1],
            "source": f"{self.source.id}_{row[3]}",
            "game_id": self.source.game_id_format.format(
                game_id=row[2], game_internal_id=row[0]
            ),
            "executable": self.source.executable_format.format(game_id=row[2]),
            "developer": None,  # TODO get developer metadata on Lutris
        }
        game = Game(self.source.win, values)

        # Save official image
        image_path = self.source.cache_location / "coverart" / f"{row[2]}.jpg"
        if image_path.exists():
            resized = resize_cover(self.source.win, image_path)
            save_cover(self.source.win, values["game_id"], resized)

        return game


class LutrisSource(Source):
    name = "Lutris"
    executable_format = "xdg-open lutris:rungameid/{game_id}"
    location = None
    cache_location = None

    @property
    def game_id_format(self):
        return super().game_id_format + "_{game_internal_id}"

    @property
    def is_installed(self):
        try:
            self.location
            self.cache_location
        except FileNotFoundError:
            return False
        else:
            return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __iter__(self):
        return LutrisSourceIterator(source=self)


class LutrisNativeSource(LutrisSource):
    """Class representing an installation of Lutris using native packaging"""

    variant = "native"

    @property
    @replaced_by_schema_key("lutris-location")
    @replaced_by_path("~/.local/share/lutris/")
    def location(self):
        raise FileNotFoundError()

    @property
    @replaced_by_schema_key("lutris-cache-location")
    @replaced_by_path("~/.local/share/lutris/covers/")
    def cache_location(self):
        raise FileNotFoundError()


class LutrisFlatpakSource(LutrisSource):
    """Class representing an installation of Lutris using flatpak"""

    variant = "flatpak"

    @property
    @replaced_by_schema_key("lutris-flatpak-location")
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris/")
    def location(self):
        raise FileNotFoundError()

    @property
    @replaced_by_schema_key("lutris-flatpak-cache-location")
    @replaced_by_path("~/.var/app/net.lutris.Lutris/data/lutris/covers/")
    def cache_location(self):
        raise FileNotFoundError()
