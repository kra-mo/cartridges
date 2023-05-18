import logging

from requests import HTTPError
from gi.repository import Adw, Gio, Gtk

from .create_dialog import create_dialog
from .steamgriddb import SGDBAuthError, SGDBError, SGDBHelper


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
    errors = None

    def __init__(self, win):
        self.win = win
        self.sources = set()
        self.errors = []

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

            # Avoid duplicates
            gid = game.game_id
            if gid in self.win.games and not self.win.games[gid].removed:
                continue

            # Register game
            self.win.games[gid] = game
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
        game.set_loading(1)
        sgdb = SGDBHelper(self.win)
        try:
            sgdb.conditionaly_update_cover(game)
        except SGDBAuthError as error:
            cancellable.cancel()
            self.errors.append(error)
        except (HTTPError, SGDBError) as error:
            self.errors.append(error)

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
