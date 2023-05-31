import json
import logging
from hashlib import sha256
from json import JSONDecodeError
from pathlib import Path
from time import time
from typing import Generator, Optional, TypedDict

from src import shared
from src.game import Game
from src.importer.sources.source import NTSource, PosixSource, Source, SourceIterator
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)
from src.utils.save_cover import resize_cover, save_cover


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
    generator: Generator = None
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

    def game_from_library_entry(self, entry: HeroicLibraryEntry) -> Optional[Game]:
        """Helper method used to build a Game from a Heroic library entry"""

        # Skip games that are not installed
        if not entry["installed"]:
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

        # Save image from the heroic cache
        # Filenames are derived from the URL that heroic used to get the file
        uri: str = entry["art_square"]
        if service == "epic":
            uri += "?h=400&resize=1&w=300"
        digest = sha256(uri.encode()).hexdigest()
        image_path = self.source.location / "images-cache" / digest
        if image_path.is_file():
            save_cover(values["game_id"], resize_cover(image_path))

        return Game(values, allow_side_effects=False)

    def sub_sources_generator(self):
        """Generator method producing games from all the Heroic sub-sources"""
        for _key, sub_source in self.sub_sources.items():
            # Skip disabled sub-sources
            if not shared.schema.get_boolean("heroic-import-" + sub_source["service"]):
                continue
            # Load games from JSON
            try:
                file = self.source.location.joinpath(*sub_source["path"])
                library = json.load(file.open())["library"]
            except (JSONDecodeError, OSError, KeyError):
                # Invalid library.json file, skip it
                continue
            for entry in library:
                try:
                    game = self.game_from_library_entry(entry)
                except KeyError:
                    # Skip invalid games
                    continue
                yield game

    def __init__(self, source: "HeroicSource") -> None:
        self.source = source
        self.generator = self.sub_sources_generator()

    def __next__(self) -> Optional[Game]:
        try:
            game = next(self.generator)
        except StopIteration:
            raise
        return game


class HeroicSource(Source):
    """Generic heroic games launcher source"""

    name = "Heroic"
    executable_format = "xdg-open heroic://launch/{app_name}"

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.name.lower() + "_{service}_{game_id}"

    def __iter__(self):
        return HeroicSourceIterator(source=self)


class HeroicNativeSource(HeroicSource, PosixSource):
    variant = "native"

    @property
    @replaced_by_schema_key("heroic-location")
    @replaced_by_env_path("XDG_CONFIG_HOME", "heroic/")
    @replaced_by_path("~/.config/heroic/")
    def location(self) -> Path:
        raise FileNotFoundError()


class HeroicFlatpakSource(HeroicSource, PosixSource):
    variant = "flatpak"

    @property
    @replaced_by_schema_key("heroic-flatpak-location")
    @replaced_by_path("~/.var/app/com.heroicgameslauncher.hgl/config/heroic/")
    def location(self) -> Path:
        raise FileNotFoundError()


class HeroicWindowsSource(HeroicSource, NTSource):
    variant = "windows"
    executable_format = "start heroic://launch/{app_name}"

    @property
    @replaced_by_schema_key("heroic-windows-location")
    @replaced_by_env_path("appdata", "heroic/")
    def location(self) -> Path:
        raise FileNotFoundError()