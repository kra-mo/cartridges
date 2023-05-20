from abc import abstractmethod
from pathlib import Path
from time import time
from typing import Iterator

from requests import HTTPError, JSONDecodeError

from src.game import Game
from src.importer.source import Source, SourceIterator
from src.utils.decorators import (
    replaced_by_env_path,
    replaced_by_path,
    replaced_by_schema_key,
)
from src.utils.save_cover import resize_cover, save_cover
from src.utils.steam import (
    SteamGameNotFoundError,
    SteamHelper,
    SteamInvalidManifestError,
    SteamNotAGameError,
)


class SteamSourceIterator(SourceIterator):
    source: "SteamSource"

    manifests: set = None
    manifests_iterator: Iterator[Path] = None
    installed_state_mask: int = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.manifests = set()

        # Get dirs that contain steam app manifests
        manifests_dirs = set()
        libraryfolders_path = self.source.location / "steamapps" / "libraryfolders.vdf"
        with open(libraryfolders_path, "r") as file:
            for line in file.readlines():
                line = line.strip()
                prefix = '"path"'
                if not line.startswith(prefix):
                    continue
                library_folder = Path(line[len(prefix) :].strip()[1:-1])
                manifests_dir = library_folder / "steamapps"
                if not (manifests_dir).is_dir():
                    continue
                manifests_dirs.add(manifests_dir)

        # Get app manifests
        for manifests_dir in manifests_dirs:
            for child in manifests_dir.iterdir():
                if child.is_file() and "appmanifest" in child.name:
                    self.manifests.add(child)

        self.manifests_iterator = iter(self.manifests)

    def __len__(self):
        return len(self.manifests)

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
        if not int(local_data["StateFlags"]) & self.installed_state_mask:
            return None

        # Build game from local data
        appid = local_data["appid"]
        values = {
            "added": int(time()),
            "name": local_data["name"],
            "source": self.source.id,
            "game_id": self.source.game_id_format.format(game_id=appid),
            "executable": self.source.executable_format.format(game_id=appid),
        }
        game = Game(self.source.win, values, allow_side_effects=False)

        # Add official cover image
        cover_path = (
            self.source.location
            / "appcache"
            / "librarycache"
            / f"{appid}_library_600x900.jpg"
        )
        if cover_path.is_file():
            save_cover(
                self.source.win, game.game_id, resize_cover(self.source.win, cover_path)
            )

        # Get online metadata
        # TODO move to its own manager
        try:
            online_data = steam.get_api_data(appid=appid)
        except (HTTPError, JSONDecodeError, SteamGameNotFoundError):
            pass
        except SteamNotAGameError:
            game.update_values({"blacklisted": True})
        else:
            game.update_values(online_data)
        return game


class SteamSource(Source):
    name = "Steam"
    executable_format = "xdg-open steam://rungameid/{game_id}"

    @property
    @abstractmethod
    def location(self) -> Path:
        pass

    @property
    def is_installed(self):
        # pylint: disable=pointless-statement
        try:
            self.location
        except FileNotFoundError:
            return False
        return True

    def __iter__(self):
        return SteamSourceIterator(source=self)


class SteamNativeSource(SteamSource):
    variant = "native"

    @property
    @replaced_by_schema_key("steam-location")
    @replaced_by_env_path("XDG_DATA_HOME", "Steam/")
    @replaced_by_path("~/.steam/")
    @replaced_by_path("~/.local/share/Steam/")
    def location(self):
        raise FileNotFoundError()


class SteamFlatpakSource(SteamSource):
    variant = "flatpak"

    @property
    @replaced_by_schema_key("steam-flatpak-location")
    @replaced_by_path("~/.var/app/com.valvesoftware.Steam/data/Steam/")
    def location(self):
        raise FileNotFoundError()


class SteamWindowsSource(SteamSource):
    variant = "windows"
    executable_format = "start steam://rungameid/{game_id}"

    @property
    @replaced_by_schema_key("steam-windows-location")
    @replaced_by_env_path("programfiles(x86)", "Steam")
    @replaced_by_path("C:\\Program Files (x86)\\Steam")
    def location(self):
        raise FileNotFoundError()
