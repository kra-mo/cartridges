import re
from pathlib import Path
from time import time
from typing import Iterator

from src import shared
from src.game import Game
from src.importer.sources.source import (
    LinuxSource,
    Source,
    SourceIterator,
    WindowsSource,
)
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)
from src.utils.save_cover import resize_cover, save_cover
from src.utils.steam import SteamHelper, SteamInvalidManifestError


class SteamSourceIterator(SourceIterator):
    source: "SteamSource"
    manifests: set = None
    manifests_iterator: Iterator[Path] = None
    installed_state_mask: int = 4
    appid_cache: set = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.appid_cache = set()
        self.manifests = set()

        # Get dirs that contain steam app manifests
        libraryfolders_path = self.source.location / "steamapps" / "libraryfolders.vdf"
        with open(libraryfolders_path, "r") as file:
            contents = file.read()
        steamapps_dirs = [
            Path(path) / "steamapps"
            for path in re.findall('"path"\s+"(.*)"\n', contents, re.IGNORECASE)
        ]

        # Get app manifests
        for steamapps_dir in steamapps_dirs:
            if not steamapps_dir.is_dir():
                continue
            self.manifests.update(
                [
                    manifest
                    for manifest in steamapps_dir.glob("appmanifest_*.acf")
                    if manifest.is_file()
                ]
            )

        self.manifests_iterator = iter(self.manifests)

    def __next__(self):
        """Produce games"""

        # Get metadata from manifest
        manifest_path = next(self.manifests_iterator)
        steam = SteamHelper()
        try:
            local_data = steam.get_manifest_data(manifest_path)
        except (OSError, SteamInvalidManifestError):
            return None

        # Skip non installed games
        if not int(local_data["stateflags"]) & self.installed_state_mask:
            return None

        # Skip duplicate appids
        appid = local_data["appid"]
        if appid in self.appid_cache:
            return None
        self.appid_cache.add(appid)

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
        cover_path = (
            self.source.location
            / "appcache"
            / "librarycache"
            / f"{appid}_library_600x900.jpg"
        )
        if cover_path.is_file():
            save_cover(game.game_id, resize_cover(cover_path))

        return game


class SteamSource(Source):
    name = "Steam"

    def __iter__(self):
        return SteamSourceIterator(source=self)


class SteamNativeSource(SteamSource, LinuxSource):
    variant = "linux"
    executable_format = "xdg-open steam://rungameid/{game_id}"

    @property
    @replaced_by_schema_key("steam-location")
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
    @replaced_by_schema_key("steam-location")
    @replaced_by_env_path("programfiles(x86)", "Steam")
    def location(self):
        raise FileNotFoundError()
