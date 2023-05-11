import logging
from pathlib import Path

import requests
from gi.repository import Adw, Gio, Gtk

from .create_dialog import create_dialog
from .save_cover import resize_cover, save_cover
from .steamgriddb import SGDBAuthError, SGDBHelper


class Importer:
    """A class in charge of scanning sources for games"""

    progressbar = None
    import_statuspage = None
    import_dialog = None

    win = None
    sources = None

    n_games_added = 0
    n_source_tasks_created = 0
    n_source_tasks_done = 0
    n_sgdb_tasks_created = 0
    n_sgdb_tasks_done = 0
    sgdb_cancellable = None
    sgdb_error = None

    def __init__(self, win):
        self.win = win
        self.sources = set()

    @property
    def n_tasks_created(self):
        return self.n_source_tasks_created + self.n_sgdb_tasks_created

    @property
    def n_tasks_done(self):
        return self.n_source_tasks_done + self.n_sgdb_tasks_done

    @property
    def progress(self):
        try:
            progress = 1 - self.n_tasks_created / self.n_tasks_done
        except ZeroDivisionError:
            progress = 1
        return progress

    @property
    def finished(self):
        return self.n_sgdb_tasks_created == self.n_tasks_done

    def add_source(self, source):
        self.sources.add(source)

    def run(self):
        """Use several Gio.Task to import games from added sources"""

        self.create_dialog()

        # Single SGDB cancellable shared by all its tasks
        # (If SGDB auth is bad, cancel all SGDB tasks)
        self.sgdb_cancellable = Gio.Cancellable()

        # Create a task for each source
        tasks = set()
        for source in self.sources:
            self.n_source_tasks_created += 1
            logging.debug("Importing games from source %s", source.id)
            task = Gio.Task(None, None, self.source_task_callback, (source,))
            task.set_task_data((source,))
            tasks.add(task)

        # Start all tasks
        for task in tasks:
            task.run_in_thread(self.source_task_thread_func)

    def create_dialog(self):
        """Create the import dialog"""
        self.progressbar = Gtk.ProgressBar(margin_start=12, margin_end=12)
        self.import_statuspage = Adw.StatusPage(
            title=_("Importing Games…"),
            child=self.progressbar,
        )
        self.import_dialog = Adw.Window(
            content=self.import_statuspage,
            modal=True,
            default_width=350,
            default_height=-1,
            transient_for=self.win,
            deletable=False,
        )
        self.import_dialog.present()

    def update_progressbar(self):
        self.progressbar.set_fraction(self.progress)

    def source_task_thread_func(self, _task, _obj, data, _cancellable):
        """Source import task code"""

        source, *_rest = data

        # Early exit if not installed
        if not source.is_installed:
            logging.info("Source %s skipped, not installed", source.id)
            return

        # Initialize source iteration
        iterator = iter(source)

        # Get games from source
        while True:
            # Handle exceptions raised when iterating
            try:
                game = next(iterator)
            except StopIteration:
                break
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logging.exception(
                    msg=f"Exception in source {source.id}",
                    exc_info=exception,
                )
                continue

            # TODO make sources return games AND avoid duplicates
            game_id = game.game_id
            if game.game_id in self.win.games and not self.win.games[game_id].removed:
                continue
            game.save()
            self.n_games_added += 1

            # Start sgdb lookup for game
            # HACK move to its own manager
            task = Gio.Task(
                None, self.sgdb_cancellable, self.sgdb_task_callback, (game,)
            )
            task.set_task_data((game,))
            task.run_in_thread(self.sgdb_task_thread_func)

    def source_task_callback(self, _obj, _result, data):
        """Source import callback"""
        _source, *_rest = data
        self.n_source_tasks_done += 1
        self.update_progressbar()
        if self.finished:
            self.import_callback()

    def sgdb_task_thread_func(self, _task, _obj, data, cancellable):
        """SGDB query code"""

        game, *_rest = data

        use_sgdb = self.win.schema.get_boolean("sgdb")
        if not use_sgdb or game.blacklisted:
            return

        # Check if we should query SGDB
        prefer_sgdb = self.win.schema.get_boolean("sgdb-prefer")
        prefer_animated = self.win.schema.get_boolean("sgdb-animated")
        image_trunk = self.win.covers_dir / game.game_id
        still = image_trunk.with_suffix(".tiff")
        animated = image_trunk.with_suffix(".gif")

        # Breaking down the condition
        is_missing = not still.is_file() and not animated.is_file()
        is_not_best = not animated.is_file() and prefer_animated
        if not (is_missing or is_not_best or prefer_sgdb):
            return

        game.set_loading(1)

        # SGDB request
        sgdb = SGDBHelper(self.win)
        try:
            sgdb_id = sgdb.get_game_id(game)
            uri = sgdb.get_game_image_uri(sgdb_id, animated=prefer_animated)
            response = requests.get(uri, timeout=5)
        except SGDBAuthError as error:
            # On auth error, cancel all present and future SGDB tasks for this import
            self.sgdb_error = error
            logging.error("SGDB Auth error occured", exc_info=error)
            cancellable.cancel()
            return
        except Exception as error:  # pylint: disable=broad-exception-caught
            logging.warning("Non auth error in SGDB query", exc_info=error)
            return

        # Image saving
        tmp_file = Gio.File.new_tmp()[0]
        tmp_file_path = tmp_file.get_path()
        Path(tmp_file_path).write_bytes(response.content)
        save_cover(self.win, game.game_id, resize_cover(self.win, tmp_file_path))

    def sgdb_task_callback(self, _obj, _result, data):
        """SGDB query callback"""
        game, *_rest = data
        game.set_loading(0)
        self.n_sgdb_tasks_done += 1
        self.update_progressbar()
        if self.finished:
            self.import_callback()

    def import_callback(self):
        """Callback called when importing has finished"""
        self.import_dialog.close()
        self.create_import_done_dialog()

    def create_import_done_dialog(self):
        if self.n_games_added == 0:
            create_dialog(
                self.win,
                _("No Games Found"),
                _("No new games were found on your system."),
                "open_preferences",
                _("Preferences"),
            ).connect("response", self.dialog_response_callback)
        elif self.n_games_added == 1:
            create_dialog(
                self.win,
                _("Game Imported"),
                _("Successfully imported 1 game."),
            ).connect("response", self.dialog_response_callback)
        elif self.n_games_added > 1:
            create_dialog(
                self.win,
                _("Games Imported"),
                # The variable is the number of games
                _("Successfully imported {} games.").format(self.n_games_added),
            ).connect("response", self.dialog_response_callback)

    def dialog_response_callback(self, _widget, response, *args):
        if response == "open_preferences":
            page, expander_row, *_rest = args
            self.win.get_application().on_preferences_action(
                page_name=page, expander_row=expander_row
            )
        # HACK SGDB manager should be in charge of its error dialog
        elif self.sgdb_error is not None:
            self.create_sgdb_error_dialog()
            self.sgdb_error = None
        # TODO additional steam libraries tip
        # (should be handled by the source somehow)

    def create_sgdb_error_dialog(self):
        create_dialog(
            self.win,
            _("Couldn't Connect to SteamGridDB"),
            str(self.sgdb_error),
            "open_preferences",
            _("Preferences"),
        ).connect("response", self.dialog_response_callback, "sgdb")
