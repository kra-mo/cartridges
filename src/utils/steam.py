import logging
import re
from time import time
from typing import TypedDict
from math import floor, ceil

import requests
from requests import HTTPError

from src import shared
from src.utils.rate_limiter import TokenBucketRateLimiter


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


class SteamRateLimiter(TokenBucketRateLimiter):
    """Rate limiter for the Steam web API"""

    # Steam web API limit
    # 200 requests per 5 min seems to be the limit
    # https://stackoverflow.com/questions/76047820/how-am-i-exceeding-steam-apis-rate-limit
    # https://stackoverflow.com/questions/51795457/avoiding-error-429-too-many-requests-steam-web-api
    REFILL_SPACING_SECONDS = 5 * 60 / 100
    MAX_TOKENS = 100

    def __init__(self) -> None:
        # Load initial tokens from schema
        # (Remember API limits through restarts of Cartridges)
        last_tokens = shared.state_schema.get_int("steam-api-tokens")
        last_time = shared.state_schema.get_int("steam-api-tokens-timestamp")
        produced = floor((time() - last_time) / self.REFILL_SPACING_SECONDS)
        inital_tokens = last_tokens + produced
        super().__init__(initial_tokens=inital_tokens)

    def refill(self):
        """Refill the bucket and store its number of tokens in the schema"""
        super().refill()
        shared.state_schema.set_int("steam-api-tokens-timestamp", ceil(time()))
        shared.state_schema.set_int("steam-api-tokens", self.n_tokens)


class SteamHelper:
    """Helper around the Steam API"""

    base_url = "https://store.steampowered.com/api"
    rate_limiter: SteamRateLimiter = None

    def __init__(self) -> None:
        # Instanciate the rate limiter on the class to share across instances
        # Can't be done at class creation time, schema isn't available yet
        if self.__class__.rate_limiter is None:
            self.__class__.rate_limiter = SteamRateLimiter()

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
        """
        Get online data for a game from its appid.
        May block to satisfy the Steam web API limitations.

        See https://wiki.teamfortress.com/wiki/User:RJackson/StorefrontAPI#appdetails
        """

        # Get data from the API (way block to satisfy its limits)
        with self.rate_limiter:
            try:
                with requests.get(
                    f"{self.base_url}/appdetails?appids={appid}", timeout=5
                ) as response:
                    response.raise_for_status()
                    data = response.json()[appid]
            except HTTPError as error:
                logging.warning("Steam API HTTP error for %s", appid, exc_info=error)
                raise error

        # Handle not found
        if not data["success"]:
            logging.debug("Appid %s not found", appid)
            raise SteamGameNotFoundError()

        # Handle appid is not a game
        game_types = ("game", "demo")
        if data["data"]["type"] not in game_types:
            logging.debug("Appid %s is not a game", appid)
            raise SteamNotAGameError()

        # Return API values we're interested in
        values = SteamAPIData(developers=", ".join(data["data"]["developers"]))
        return values
