import re
import logging
from typing import TypedDict

import requests
from requests import HTTPError, JSONDecodeError


class SteamError(Exception):
    pass


class SteamGameNotFoundError(SteamError):
    pass


class SteamNotAGameError(SteamError):
    pass


class SteamInvalidManifestError(SteamError):
    pass


class SteamManifestData(TypedDict):
    """Dict returned by SteamHelper.get_manifest_data"""

    name: str
    appid: str
    stateflags: str


class SteamAPIData(TypedDict):
    """Dict returned by SteamHelper.get_api_data"""

    developers: str


class SteamHelper:
    """Helper around the Steam API"""

    base_url = "https://store.steampowered.com/api"

    def get_manifest_data(self, manifest_path) -> SteamManifestData:
        """Get local data for a game from its manifest"""

        with open(manifest_path) as file:
            contents = file.read()

        data = {}

        for key in SteamManifestData.__required_keys__:
            regex = f'"{key}"\s+"(.*)"\n'
            if (match := re.search(regex, contents, re.IGNORECASE)) is None:
                raise SteamInvalidManifestError()
            data[key] = match.group(1)

        return SteamManifestData(**data)

    def get_api_data(self, appid) -> SteamAPIData:
        """Get online data for a game from its appid"""

        try:
            with requests.get(
                f"{self.base_url}/appdetails?appids={appid}", timeout=5
            ) as response:
                response.raise_for_status()
                data = response.json()[appid]
        except HTTPError as error:
            logging.warning("Steam API HTTP error for %s", appid, exc_info=error)
            raise error
        if not data["success"]:
            logging.debug("Appid %s not found", appid)
            raise SteamGameNotFoundError()

        game_types = ("game", "demo")
        if data["data"]["type"] not in game_types:
            logging.debug("Appid %s is not a game", appid)
            raise SteamNotAGameError()

        # Return API values we're interested in
        values = SteamAPIData(developers=", ".join(data["data"]["developers"]))
        return values
