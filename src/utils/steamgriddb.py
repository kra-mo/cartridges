from pathlib import Path

import requests
from gi.repository import Gio

from . import shared
from .create_dialog import create_dialog
from .save_cover import save_cover, resize_cover


class SGDBError(Exception):
    pass


class SGDBHelper:
    """Helper class to make queries to SteamGridDB"""

    base_url = "https://www.steamgriddb.com/api/v2/"
    win = None

    def __init__(self, win):
        self.win = win

    @property
    def auth_headers(self):
        key = self.win.schema.get_string("sgdb-key")
        headers = {"Authorization": f"Bearer {key}"}
        return headers

    # TODO delegate that to the app
    def create_exception_dialog(self, exception):
        dialog = create_dialog(
            self.win,
            _("Couldn't Connect to SteamGridDB"),
            exception,
            "open_preferences",
            _("Preferences"),
        )
        dialog.connect("response", self.on_exception_dialog_response)

    # TODO same as create_exception_dialog
    def on_exception_dialog_response(self, _widget, response):
        if response == "open_preferences":
            self.win.get_application().on_preferences_action(page_name="sgdb")

    def get_game_id(self, game):
        """Get grid results for a game. Can raise an exception."""

        # Request
        res = requests.get(
            f"{self.base_url}search/autocomplete/{game.name}",
            headers=self.auth_headers,
            timeout=5,
        )
        if res.status_code == 200:
            return res.json()["data"][0]["id"]

        # HTTP error
        res.raise_for_status()

        # SGDB API error
        res_json = res.json()
        if "error" in tuple(res_json):
            raise SGDBError(res_json["errors"])
        raise SGDBError(res.status_code)

    def get_game_image_uri(self, game, animated=False):
        """Get the image for a game"""
        game_id = self.get_game_id(game)
        uri = f"{self.base_url}grids/game/{game_id}?dimensions=600x900"
        if animated:
            uri += "&types=animated"
        grid = requests.get(uri, headers=self.auth_headers, timeout=5)
        image_uri = grid.json()["data"][0]["url"]
        return image_uri


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
