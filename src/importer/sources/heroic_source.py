import json
import logging
from hashlib import sha256
from json import JSONDecodeError
from pathlib import Path
from time import time
from typing import Optional, TypedDict

from src import shared
from src.game import Game
from src.importer.sources.source import (
    URLExecutableSource,
    SourceIterationResult,
    SourceIterator,
)
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)


class HeroicLibraryEntry(TypedDict):
    app_name: str
    installed: Optional[bool]
    runner: str
    title: str
    developer: str
    art_square: str


class HeroicSubSource(TypedDict):
    service: str
    path: tuple[str]


class HeroicSourceIterator(SourceIterator):
    source: "HeroicSource"

    sub_sources: dict[str, HeroicSubSource] = {
        "sideload": {
            "service": "sideload",
            "path": ("sideload_apps", "library.json"),
        },
        "legendary": {
            "service": "epic",
            "path": ("store_cache", "legendary_library.json"),
        },
        "gog": {
            "service": "gog",
            "path": ("store_cache", "gog_library.json"),
        },
    }

    def game_from_library_entry(
        self, entry: HeroicLibraryEntry
    ) -> SourceIterationResult:
        """Helper method used to build a Game from a Heroic library entry"""

        # Skip games that are not installed
        if not entry["is_installed"]:
            return None

        # Build game
        app_name = entry["app_name"]
        runner = entry["runner"]
        service = self.sub_sources[runner]["service"]
        values = {
            "version": shared.SPEC_VERSION,
            "source": self.source.id,
            "added": int(time()),
            "name": entry["title"],
            "developer": entry["developer"],
            "game_id": self.source.game_id_format.format(
                service=service, game_id=app_name
            ),
            "executable": self.source.executable_format.format(app_name=app_name),
        }
        game = Game(values, allow_side_effects=False)

        # Get the image path from the heroic cache
        # Filenames are derived from the URL that heroic used to get the file
        uri: str = entry["art_square"]
        if service == "epic":
            uri += "?h=400&resize=1&w=300"
        digest = sha256(uri.encode()).hexdigest()
        image_path = self.source.location / "images-cache" / digest
        additional_data = {"local_image_path": image_path}

        return (game, additional_data)

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games from all the Heroic sub-sources"""

        for sub_source in self.sub_sources.values():
            # Skip disabled sub-sources
            if not shared.schema.get_boolean("heroic-import-" + sub_source["service"]):
                continue
            # Load games from JSON
            file = self.source.location.joinpath(*sub_source["path"])
            try:
                library = json.load(file.open())["library"]
            except (JSONDecodeError, OSError, KeyError):
                # Invalid library.json file, skip it
                logging.warning("Couldn't open Heroic file: %s", str(file))
                continue
            for entry in library:
                try:
                    result = self.game_from_library_entry(entry)
                except KeyError:
                    # Skip invalid games
                    logging.warning("Invalid Heroic game skipped in %s", str(file))
                    continue
                yield result


class HeroicSource(URLExecutableSource):
    """Generic heroic games launcher source"""

    name = "Heroic"
    iterator_class = HeroicSourceIterator
    url_format = "heroic://launch/{app_name}"
    available_on = set(("linux", "win32"))

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.name.lower() + "_{service}_{game_id}"

    @property
    @replaced_by_schema_key
    @replaced_by_path("~/.var/app/com.heroicgameslauncher.hgl/config/heroic/")
    @replaced_by_env_path("XDG_CONFIG_HOME", "heroic/")
    @replaced_by_path("~/.config/heroic/")
    @replaced_by_env_path("appdata", "heroic/")
    def location(self) -> Path:
        raise FileNotFoundError()
