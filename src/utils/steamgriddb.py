import logging
from pathlib import Path

import requests
from gi.repository import Gio
from requests import HTTPError

from src import shared
from src.utils.create_dialog import create_dialog
from src.utils.save_cover import resize_cover, save_cover


class SGDBError(Exception):
    pass


class SGDBAuthError(SGDBError):
    pass


class SGDBGameNotFoundError(SGDBError):
    pass


class SGDBBadRequestError(SGDBError):
    pass


class SGDBNoImageFoundError(SGDBError):
    pass


class SGDBHelper:
    """Helper class to make queries to SteamGridDB"""

    base_url = "https://www.steamgriddb.com/api/v2/"

    @property
    def auth_headers(self):
        key = shared.schema.get_string("sgdb-key")
        headers = {"Authorization": f"Bearer {key}"}
        return headers

    def get_game_id(self, game):
        """Get grid results for a game. Can raise an exception."""
        uri = f"{self.base_url}search/autocomplete/{game.name}"
        res = requests.get(uri, headers=self.auth_headers, timeout=5)
        match res.status_code:
            case 200:
                return res.json()["data"][0]["id"]
            case 401:
                raise SGDBAuthError(res.json()["errors"][0])
            case 404:
                raise SGDBGameNotFoundError(res.status_code)
            case _:
                res.raise_for_status()

    def get_image_uri(self, game_id, animated=False):
        """Get the image for a SGDB game id"""
        uri = f"{self.base_url}grids/game/{game_id}?dimensions=600x900"
        if animated:
            uri += "&types=animated"
        res = requests.get(uri, headers=self.auth_headers, timeout=5)
        match res.status_code:
            case 200:
                data = res.json()["data"]
                if len(data) == 0:
                    raise SGDBNoImageFoundError()
                return data[0]["url"]
            case 401:
                raise SGDBAuthError(res.json()["errors"][0])
            case 404:
                raise SGDBGameNotFoundError(res.status_code)
            case _:
                res.raise_for_status()

    def conditionaly_update_cover(self, game):
        """Update the game's cover if appropriate"""

        # Obvious skips
        use_sgdb = shared.schema.get_boolean("sgdb")
        if not use_sgdb or game.blacklisted:
            return

        image_trunk = shared.covers_dir / game.game_id
        still = image_trunk.with_suffix(".tiff")
        uri_kwargs = image_trunk.with_suffix(".gif")
        prefer_sgdb = shared.schema.get_boolean("sgdb-prefer")

        # Do nothing if file present and not prefer SGDB
        if not prefer_sgdb and (still.is_file() or uri_kwargs.is_file()):
            return

        # Get ID for the game
        try:
            sgdb_id = self.get_game_id(game)
        except (HTTPError, SGDBError) as error:
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
                save_cover(game.game_id, resize_cover(tmp_file_path))
            except SGDBAuthError as error:
                # Let caller handle auth errors
                raise error
            except (HTTPError, SGDBError) as error:
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
        raise SGDBNoImageFoundError()


# Current steps to save image for N games
# Create a task for every game
# Call update_cover
# If using sgdb and (prefer or no image) and not blacklisted
# Search for game
# Get image from sgdb (animated if preferred and found, or still)
# Exit task and enter task_done
# If error, create popup


class SGDBSave:
    def __init__(self, games, importer=None):
        self.win = shared.win
        self.importer = importer
        self.exception = None

        # Wrap the function in another one as Gio.Task.run_in_thread does not allow for passing args
        def create_func(game):
            def wrapper(task, *_args):
                self.update_cover(
                    task,
                    game,
                )

            return wrapper

        for game in games:
            Gio.Task.new(None, None, self.task_done).run_in_thread(create_func(game))

    def update_cover(self, task, game):
        game.set_loading(1)

        if (
            not (
                shared.schema.get_boolean("sgdb")
                and (
                    (shared.schema.get_boolean("sgdb-prefer"))
                    or not (
                        (shared.covers_dir / f"{game.game_id}.gif").is_file()
                        or (shared.covers_dir / f"{game.game_id}.tiff").is_file()
                    )
                )
            )
            or game.blacklisted
        ):
            task.return_value(game)
            return

        url = "https://www.steamgriddb.com/api/v2/"
        headers = {"Authorization": f'Bearer {shared.schema.get_string("sgdb-key")}'}

        try:
            search_result = requests.get(
                f"{url}search/autocomplete/{game.name}",
                headers=headers,
                timeout=5,
            )
            if search_result.status_code != 200:
                self.exception = str(
                    search_result.json()["errors"][0]
                    if "errors" in tuple(search_result.json())
                    else search_result.status_code
                )
            search_result.raise_for_status()
        except requests.exceptions.RequestException:
            task.return_value(game)
            return

        response = None

        try:
            if shared.schema.get_boolean("sgdb-animated"):
                try:
                    grid = requests.get(
                        f'{url}grids/game/{search_result.json()["data"][0]["id"]}?dimensions=600x900&types=animated',
                        headers=headers,
                        timeout=5,
                    )
                    response = requests.get(grid.json()["data"][0]["url"], timeout=5)
                except IndexError:
                    pass
            if not response:
                grid = requests.get(
                    f'{url}grids/game/{search_result.json()["data"][0]["id"]}?dimensions=600x900',
                    headers=headers,
                    timeout=5,
                )
                response = requests.get(grid.json()["data"][0]["url"], timeout=5)
        except (requests.exceptions.RequestException, IndexError):
            task.return_value(game)
            return

        tmp_file = Gio.File.new_tmp()[0]
        Path(tmp_file.get_path()).write_bytes(response.content)

        save_cover(
            game.game_id,
            resize_cover(tmp_file.get_path()),
        )

        task.return_value(game)

    def task_done(self, _task, result):
        if self.importer:
            self.importer.queue -= 1
            self.importer.done()
            self.importer.sgdb_exception = self.exception

            if self.exception and not self.importer:
                create_dialog(
                    self.win,
                    _("Couldn't Connect to SteamGridDB"),
                    self.exception,
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", self.response)

        game = result.propagate_value()[1]
        game.set_loading(-1)

        if self.importer:
            game.save()
        else:
            game.update()

    def response(self, _widget, response):
        if response == "open_preferences":
            self.win.get_application().on_preferences_action(page_name="sgdb")
