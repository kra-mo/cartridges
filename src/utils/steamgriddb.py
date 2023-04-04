from pathlib import Path

import requests
from gi.repository import Gio
from steamgrid import SteamGridDB, http

from .create_dialog import create_dialog
from .save_cover import save_cover


class SGDBSave:
    def __init__(self, parent_widget, games, importer=None):
        self.parent_widget = parent_widget
        self.sgdb = SteamGridDB(self.parent_widget.schema.get_string("sgdb-key"))
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
        if self.parent_widget.schema.get_boolean("sgdb-prefer") or (
            self.parent_widget.schema.get_boolean("sgdb-import")
            and not (
                self.parent_widget.data_dir
                / "cartridges"
                / "covers"
                / f"{game[0]}.tiff"
            ).is_file()
        ):
            try:
                search_result = self.sgdb.search_game(game[1])
            except requests.exceptions.RequestException:
                task.return_value(game[0])
                return
            except http.HTTPException as exception:
                self.exception = str(exception)
                task.return_value(game[0])
                return

            try:
                grid = self.sgdb.get_grids_by_gameid(
                    [search_result[0].id], is_nsfw=False
                )[0]
            except (TypeError, IndexError):
                task.return_value(game[0])
                return

            tmp_file = Gio.File.new_tmp(None)[0]

            try:
                response = requests.get(str(grid), timeout=5)
            except requests.exceptions.RequestException:
                task.return_value(game[0])
                return

            Path(tmp_file.get_path()).write_bytes(response.content)
            save_cover(self.parent_widget, game[0], tmp_file.get_path())

        task.return_value(game[0])

    def task_done(self, _task, result):
        game_id = result.propagate_value()[1]
        self.parent_widget.update_games([game_id])
        if self.importer:
            self.importer.queue -= 1
            self.importer.done()
            self.importer.sgdb_exception = self.exception
        elif self.exception:
            create_dialog(
                self.parent_widget,
                _("Couldn't Connect to SteamGridDB"),
                self.exception,
                "open_preferences",
                _("Preferences"),
            ).connect("response", self.response)

    def response(self, _widget, response):
        if response == "open_preferences":
            self.parent_widget.get_application().on_preferences_action(
                None, page_name="sgdb"
            )
