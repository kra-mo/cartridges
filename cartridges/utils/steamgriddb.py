# steamgriddb.py
#
# Copyright 2022-2023 kramo
# Copyright 2023 Geoffrey Coulaud
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import logging
from pathlib import Path
from typing import Any

import requests
from gi.repository import Gio
from requests.exceptions import HTTPError

from cartridges import shared
from cartridges.game import Game
from cartridges.utils.save_cover import convert_cover, save_cover


class SgdbError(Exception):
    pass


class SgdbAuthError(SgdbError):
    pass


class SgdbGameNotFound(SgdbError):
    pass


class SgdbBadRequest(SgdbError):
    pass


class SgdbNoImageFound(SgdbError):
    pass


class SgdbHelper:
    """Helper class to make queries to SteamGridDB"""

    base_url = "https://www.steamgriddb.com/api/v2/"

    @property
    def auth_headers(self) -> dict[str, str]:
        key = shared.schema.get_string("sgdb-key")
        headers = {"Authorization": f"Bearer {key}"}
        return headers

    def get_game_id(self, game: Game) -> Any:
        """Get grid results for a game. Can raise an exception."""
        uri = f"{self.base_url}search/autocomplete/{game.name}"
        res = requests.get(uri, headers=self.auth_headers, timeout=5)
        match res.status_code:
            case 200:
                return res.json()["data"][0]["id"]
            case 401:
                raise SgdbAuthError(res.json()["errors"][0])
            case 404:
                raise SgdbGameNotFound(res.status_code)
            case _:
                res.raise_for_status()

    def get_image_uri(self, game_id: str, animated: bool = False) -> Any:
        """Get the image for a SGDB game id"""
        uri = f"{self.base_url}grids/game/{game_id}?dimensions=600x900"
        if animated:
            uri += "&types=animated"
        res = requests.get(uri, headers=self.auth_headers, timeout=5)
        match res.status_code:
            case 200:
                data = res.json()["data"]
                if len(data) == 0:
                    raise SgdbNoImageFound()
                return data[0]["url"]
            case 401:
                raise SgdbAuthError(res.json()["errors"][0])
            case 404:
                raise SgdbGameNotFound(res.status_code)
            case _:
                res.raise_for_status()

    def conditionaly_update_cover(self, game: Game) -> None:
        """Update the game's cover if appropriate"""

        # Obvious skips
        use_sgdb = shared.schema.get_boolean("sgdb")
        if not use_sgdb or game.blacklisted:
            return

        image_trunk = shared.covers_dir / game.game_id
        still = image_trunk.with_suffix(".tiff")
        animated = image_trunk.with_suffix(".gif")
        prefer_sgdb = shared.schema.get_boolean("sgdb-prefer")

        # Do nothing if file present and not prefer SGDB
        if not prefer_sgdb and (still.is_file() or animated.is_file()):
            return

        # Get ID for the game
        try:
            sgdb_id = self.get_game_id(game)
        except (HTTPError, SgdbError) as error:
            logging.warning(
                "%s while getting SGDB ID for %s", type(error).__name__, game.name
            )
            raise error

        # Build different SGDB options to try
        image_uri_kwargs_sets = [{"animated": False}]
        if shared.schema.get_boolean("sgdb-animated"):
            image_uri_kwargs_sets.insert(0, {"animated": True})

        # Download covers
        for uri_kwargs in image_uri_kwargs_sets:
            try:
                uri = self.get_image_uri(sgdb_id, **uri_kwargs)
                response = requests.get(uri, timeout=5)
                tmp_file = Gio.File.new_tmp()[0]
                tmp_file_path = tmp_file.get_path()
                Path(tmp_file_path).write_bytes(response.content)
                save_cover(game.game_id, convert_cover(tmp_file_path))
            except SgdbAuthError as error:
                # Let caller handle auth errors
                raise error
            except (HTTPError, SgdbError) as error:
                logging.warning(
                    "%s while getting image for %s kwargs=%s",
                    type(error).__name__,
                    game.name,
                    str(uri_kwargs),
                )
                continue
            else:
                # Stop as soon as one is finished
                return

        # No image was added
        logging.warning(
            'No matching image found for game "%s" (SGDB ID %d)',
            game.name,
            sgdb_id,
        )
        raise SgdbNoImageFound()
