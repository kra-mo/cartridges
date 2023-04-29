from pathlib import Path
from functools import cached_property
from sqlite3 import connect

from cartridges.game2 import Game
from cartridges.importer.source import Source, SourceIterator


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

    location = None
    cache_location = None

    def __iter__(self):
        return LutrisSourceIterator(source=self)

    # TODO find a way to no duplicate this code
    # Ideas: 
    # - Location class (verbose, set in __init__)
    # - Schema key override decorator ()

    # Lutris location property
    @cached_property
    def location(self):
        ovr = Path(self.win.schema.get_string(self.location_key))
        if ovr.exists(): return ovr
        return self.location_default

    # Lutris cache location property
    @cached_property
    def cache_location(self):
        ovr = Path(self.win.schema.get_string(self.cache_location_key))
        if ovr.exists(): return ovr
        return self.cache_location_default


class LutrisNativeSource(LutrisSource):
    variant = "native"
    location_key = "lutris-location"
    location_default = Path("~/.local/share/lutris/").expanduser()
    cache_location_key = "lutris-cache-location"
    cache_location_default = location_default / "covers"


class LutrisFlatpakSource(LutrisSource):
    variant = "flatpak"
    location_key = "lutris-flatpak-location"
    location_default = Path("~/.var/app/net.lutris.Lutris/data/lutris").expanduser()
    cache_location_key = "lutris-flatpak-cache-location"
    cache_location_default = location_default / "covers"