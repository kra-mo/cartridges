import re
from pathlib import Path
from time import time
from typing import Iterable

from src import shared  # pylint: disable=no-name-in-module
from src.game import Game
from src.importer.sources.source import (
    SourceIterationResult,
    SourceIterator,
    URLExecutableSource,
)
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)
from src.utils.steam import SteamFileHelper, SteamInvalidManifestError


class SteamSourceIterator(SourceIterator):
    source: "SteamSource"

    def get_manifest_dirs(self) -> Iterable[Path]:
        """Get dirs that contain steam app manifests"""
        libraryfolders_path = self.source.location / "steamapps" / "libraryfolders.vdf"
        with open(libraryfolders_path, "r", encoding="utf-8") as file:
            contents = file.read()
        return [
            Path(path) / "steamapps"
            for path in re.findall('"path"\\s+"(.*)"\n', contents, re.IGNORECASE)
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

    def generator_builder(self) -> SourceIterationResult:
        """Generator method producing games"""
        appid_cache = set()
        manifests = self.get_manifests()
        for manifest in manifests:
            # Get metadata from manifest
            steam = SteamFileHelper()
            try:
                local_data = steam.get_manifest_data(manifest)
            except (OSError, SteamInvalidManifestError):
                continue

            # Skip non installed games
            installed_mask = 4
            if not int(local_data["stateflags"]) & installed_mask:
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
            additional_data = {"local_image_path": image_path, "steam_appid": appid}

            # Produce game
            yield (game, additional_data)


class SteamSource(URLExecutableSource):
    name = "Steam"
    iterator_class = SteamSourceIterator
    url_format = "steam://rungameid/{game_id}"
    available_on = set(("linux", "win32"))

    @property
    @replaced_by_schema_key
    @replaced_by_path("~/.var/app/com.valvesoftware.Steam/data/Steam/")
    @replaced_by_env_path("XDG_DATA_HOME", "Steam/")
    @replaced_by_path("~/.steam/")
    @replaced_by_path("~/.local/share/Steam/")
    @replaced_by_env_path("programfiles(x86)", "Steam")
    def location(self):
        raise FileNotFoundError()
