from pathlib import Path
from functools import cached_property
from sqlite3 import connect

from cartridges.game2 import Game
from cartridges.importer.source import Source, SourceIterator
from cartridges.importer.location import Location


class LutrisSourceIterator(SourceIterator):

    ignore_steam_games = False

    db_connection = None
    db_cursor = None
    db_location = None
    db_request = None

    def __init__(self, ignore_steam_games) -> None:
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

        # Get next DB value
        while True:
            try:
                row = self.db_cursor.__next__() 
            except StopIteration as e:
                self.db_connection.close()
                raise e

            # Ignore steam games if requested
            if row[3] == "steam" and self.ignore_steam_games:
                continue
            
            # Build basic game
            game = Game(
                name=row[1],
                hidden=row[4],
                source=self.source.full_name,
                game_id=self.source.game_id_format.format(game_id=row[2]),
                executable=self.source.executable_format.format(game_id=row[2]),
                developer=None, # TODO get developer metadata on Lutris
            )
            # TODO Add official image
            # TODO Add SGDB image  
            return game

class LutrisSource(Source):
    
    name = "Lutris"
    executable_format = "xdg-open lutris:rungameid/{game_id}"
    schema_keys = {
        "location": None,
        "cache_location": None
    }

    def __init__(self, win) -> None:
        super().__init__(win)
        self.location = Location()
        self.cache_location = Location()

    def __iter__(self):
        return LutrisSourceIterator(source=self)

    def __init_locations__(self):
        super().__init_locations__()
        self.location.add_override(self.win.schema.get_string(self.schema_keys["location"]))
        self.cache_location.add_override(self.win.schema.get_string(self.schema_keys["cache_location"]))


class LutrisNativeSource(LutrisSource):
    """Class representing an installation of Lutris using native packaging"""

    variant = "native"
    schema_keys = {
        "location": "lutris-location",
        "cache_location": "lutris-cache-location"
    }

    def __init_locations__(self):
        super().__init_locations__()
        self.location.add("~/.local/share/lutris/")
        self.cache_location.add("~/.local/share/lutris/covers")


class LutrisFlatpakSource(LutrisSource):
    """Class representing an installation of Lutris using flatpak"""

    variant = "flatpak"
    schema_keys = {
        "location": "lutris-flatpak-location",
        "cache_location": "lutris-flatpak-cache-location"
    }

    def __init_locations__(self):
        super().__init_locations__()
        self.location.add("~/.var/app/net.lutris.Lutris/data/lutris")
        self.cache_location.add("~/.var/app/net.lutris.Lutris/data/lutris/covers")