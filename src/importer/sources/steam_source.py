import re
from pathlib import Path
from time import time
from typing import Iterable, Optional

from src import shared
from src.game import Game
from src.importer.sources.source import (
    LinuxSource,
    Source,
    SourceIterator,
    WindowsSource,
)
from src.utils.decorators import replaced_by_env_path, replaced_by_path
from src.utils.save_cover import resize_cover, save_cover
from src.utils.steam import SteamHelper, SteamInvalidManifestError


class SteamSourceIterator(SourceIterator):
    source: "SteamSource"

    def get_manifest_dirs(self) -> Iterable[Path]:
        """Get dirs that contain steam app manifests"""
        libraryfolders_path = self.source.location / "steamapps" / "libraryfolders.vdf"
        with open(libraryfolders_path, "r") as file:
            contents = file.read()
        return [
            Path(path) / "steamapps"
            for path in re.findall('"path"\s+"(.*)"\n', contents, re.IGNORECASE)
        ]

    def get_manifests(self) -> Iterable[Path]:
        """Get app manifests"""
        manifests = set()
        for steamapps_dir in self.get_manifest_dirs():
            if not steamapps_dir.is_dir():
                continue
            manifests.update(
                [
                    manifest
                    for manifest in steamapps_dir.glob("appmanifest_*.acf")
                    if manifest.is_file()
                ]
            )
        return manifests

    def generator_builder(self) -> Optional[Game]:
        """Generator method producing games"""
        appid_cache = set()
        manifests = self.get_manifests()
        for manifest in manifests:
            # Get metadata from manifest
            steam = SteamHelper()
            try:
                local_data = steam.get_manifest_data(manifest)
            except (OSError, SteamInvalidManifestError):
                continue

            # Skip non installed games
            INSTALLED_MASK: int = 4
            if not int(local_data["stateflags"]) & INSTALLED_MASK:
                continue

            # Skip duplicate appids
            appid = local_data["appid"]
            if appid in appid_cache:
                continue
            appid_cache.add(appid)

            # Build game from local data
            values = {
                "version": shared.SPEC_VERSION,
                "added": int(time()),
                "name": local_data["name"],
                "source": self.source.id,
                "game_id": self.source.game_id_format.format(game_id=appid),
                "executable": self.source.executable_format.format(game_id=appid),
            }
            game = Game(values, allow_side_effects=False)

            # Add official cover image
            image_path = (
                self.source.location
                / "appcache"
                / "librarycache"
                / f"{appid}_library_600x900.jpg"
            )
            if image_path.is_file():
                save_cover(game.game_id, resize_cover(image_path))

            # Produce game
            yield game


class SteamSource(Source):
    name = "Steam"
    location_key = "steam-location"

    def __iter__(self):
        return SteamSourceIterator(source=self)


class SteamLinuxSource(SteamSource, LinuxSource):
    variant = "linux"
    executable_format = "xdg-open steam://rungameid/{game_id}"

    @property
    @Source.replaced_by_schema_key()
    @replaced_by_path("~/.var/app/com.valvesoftware.Steam/data/Steam/")
    @replaced_by_env_path("XDG_DATA_HOME", "Steam/")
    @replaced_by_path("~/.steam/")
    @replaced_by_path("~/.local/share/Steam/")
    def location(self):
        raise FileNotFoundError()


class SteamWindowsSource(SteamSource, WindowsSource):
    variant = "windows"
    executable_format = "start steam://rungameid/{game_id}"

    @property
    @Source.replaced_by_schema_key()
    @replaced_by_env_path("programfiles(x86)", "Steam")
    def location(self):
        raise FileNotFoundError()
