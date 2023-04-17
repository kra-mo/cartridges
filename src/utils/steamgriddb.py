from pathlib import Path

import requests
from gi.repository import Gio

from .create_dialog import create_dialog
from .save_cover import save_cover, resize_cover


class SGDBSave:
    def __init__(self, win, games, importer=None):
        self.win = win
        self.importer = importer
        self.exception = None

        # Wrap the function in another one as Gio.Task.run_in_thread does not allow for passing args
        def create_func(game):
            def wrapper(task, *_unused):
                self.update_cover(
                    task,
                    game,
                )

            return wrapper

        for game in games:
            Gio.Task.new(None, None, self.task_done).run_in_thread(create_func(game))

    def update_cover(self, task, game):
        if self.win.schema.get_boolean("sgdb") and (
            self.win.schema.get_boolean("sgdb-prefer")
            or (
                not (self.win.covers_dir / f"{game[0]}.gif").is_file()
                and not (self.win.covers_dir / f"{game[0]}.tiff").is_file()
            )
        ):
            if not self.importer:
                self.win.games[game[0]].set_loading(1)

            url = "https://www.steamgriddb.com/api/v2/"
            headers = {
                "Authorization": f'Bearer {self.win.schema.get_string("sgdb-key")}'
            }

            try:
                search_result = requests.get(
                    f"{url}search/autocomplete/{game[1]}",
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
                task.return_value(game[0])
                return

            response = None

            try:
                if self.win.schema.get_boolean("sgdb-animated"):
                    try:
                        grid = requests.get(
                            f'{url}grids/game/{search_result.json()["data"][0]["id"]}?dimensions=600x900&types=animated',
                            headers=headers,
                            timeout=5,
                        )
                        response = requests.get(
                            grid.json()["data"][0]["url"], timeout=5
                        )
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
                task.return_value(game[0])
                return

            tmp_file = Gio.File.new_tmp(None)[0]
            Path(tmp_file.get_path()).write_bytes(response.content)

            save_cover(
                self.win,
                game[0],
                resize_cover(self.win, tmp_file.get_path()),
            )

        task.return_value(game[0])

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

        game_id = result.propagate_value()[1]
        self.win.update_games([game_id])

    def response(self, _widget, response):
        if response == "open_preferences":
            self.win.get_application().on_preferences_action(None, page_name="sgdb")
