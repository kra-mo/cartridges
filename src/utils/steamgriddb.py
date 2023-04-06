from pathlib import Path

import requests
from gi.repository import Gio

from .create_dialog import create_dialog
from .save_cover import save_cover


class SGDBSave:
    def __init__(self, parent_widget, games, importer=None):
        self.parent_widget = parent_widget
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
        if self.parent_widget.schema.get_boolean("sgdb") and (
            self.parent_widget.schema.get_boolean("sgdb-prefer")
            or not (
                self.parent_widget.data_dir
                / "cartridges"
                / "covers"
                / f"{game[0]}.tiff"
            ).is_file()
        ):
            if not self.importer:
                self.parent_widget.loading = game[0]

            url = "https://www.steamgriddb.com/api/v2/"
            headers = {
                "Authorization": f'Bearer {self.parent_widget.schema.get_string("sgdb-key")}'
            }

            try:
                search_result = requests.get(
                    f"{url}search/autocomplete/{game[1]}",
                    headers=headers,
                    timeout=5,
                )
                search_result.raise_for_status()
            except requests.exceptions.RequestException:
                if search_result.status_code != 200:
                    self.exception = str(
                        search_result.json()["errors"][0]
                        if "errors" in tuple(search_result.json())
                        else search_result.status_code
                    )
                task.return_value(game[0])
                return

            try:
                headers["dimensions"] = "600x900"
                grid = requests.get(
                    f'{url}grids/game/{search_result.json()["data"][0]["id"]}',
                    headers=headers,
                    timeout=5,
                )
            except (requests.exceptions.RequestException, IndexError):
                task.return_value(game[0])
                return

            tmp_file = Gio.File.new_tmp(None)[0]

            try:
                response = requests.get(
                    grid.json()["data"][0]["url"],
                    timeout=5,
                )
            except (requests.exceptions.RequestException, IndexError):
                task.return_value(game[0])
                return

            Path(tmp_file.get_path()).write_bytes(response.content)
            save_cover(self.parent_widget, game[0], tmp_file.get_path())

        task.return_value(game[0])

    def task_done(self, _task, result):
        if self.importer:
            self.importer.queue -= 1
            self.importer.done()
            self.importer.sgdb_exception = self.exception
        else:
            self.parent_widget.loading = None

            if self.exception:
                create_dialog(
                    self.parent_widget,
                    _("Couldn't Connect to SteamGridDB"),
                    self.exception,
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", self.response)

        game_id = result.propagate_value()[1]
        self.parent_widget.update_games([game_id])

    def response(self, _widget, response):
        if response == "open_preferences":
            self.parent_widget.get_application().on_preferences_action(
                None, page_name="sgdb"
            )
