import re
import logging
from time import time
from pathlib import Path

import requests
from requests import HTTPError, JSONDecodeError

from src.game import Game
from src.importer.source import Source, SourceIterator
from src.utils.decorators import (
    replaced_by_path,
    replaced_by_schema_key,
    replaced_by_env_path,
)
from src.utils.save_cover import resize_cover, save_cover


class SteamAPIError(Exception):
    pass


class SteamSourceIterator(SourceIterator):
    source: "SteamSource"

    manifests = None
    manifests_iterator = None

    installed_state_mask = 4

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
        # Get metadata from manifest
        # Ignore manifests that don't have a value for all keys
        manifest = next(self.manifests_iterator)
        manifest_data = {"name": None, "appid": None, "StateFlags": "0"}
        try:
            with open(manifest) as file:
                contents = file.read()
                for key in manifest_data:
                    regex = f'"{key}"\s+"(.*)"\n'
                    if (match := re.search(regex, contents)) is None:
                        return None
                    manifest_data[key] = match.group(1)
        except OSError:
            return None

        # Skip non installed games
        if not int(manifest_data["StateFlags"]) & self.installed_state_mask:
            return None

        # Build basic game
        appid = manifest_data["appid"]
        values = {
            "added": int(time()),
            "name": manifest_data["name"],
            "hidden": False,
            "source": self.source.id,
            "game_id": self.source.game_id_format.format(game_id=appid),
            "executable": self.source.executable_format.format(game_id=appid),
            "blacklisted": False,
            "developer": None,
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
            save_cover(self.win, game.game_id, resize_cover(self.win, cover_path))

        # Make Steam API call
        try:
            with requests.get(
                "https://store.steampowered.com/api/appdetails?appids=%s"
                % manifest_data["appid"],
                timeout=5,
            ) as response:
                response.raise_for_status()
                steam_api_data = response.json()[appid]
        except (HTTPError, JSONDecodeError) as error:
            logging.warning(
                "Error while querying Steam API for %s (%s)",
                manifest_data["name"],
                manifest_data["appid"],
                exc_info=error,
            )
            return game

        # Fill out new values
        if not steam_api_data["success"] or steam_api_data["data"]["type"] != "game":
            values["blacklisted"] = True
        else:
            values["developer"] = ", ".join(steam_api_data["data"]["developers"])
        game.update_values(values)
        return game


class SteamSource(Source):
    name = "Steam"
    executable_format = "xdg-open steam://rungameid/{game_id}"
    location = None

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

    @property
    @replaced_by_schema_key("steam-windows-location")
    @replaced_by_env_path("programfiles(x86)", "Steam")
    def location(self):
        raise FileNotFoundError()
