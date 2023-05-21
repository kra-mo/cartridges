import logging

from gi.repository import Adw, Gio, Gtk
from requests import HTTPError

import src.shared as shared
from src.utils.create_dialog import create_dialog
from src.utils.steamgriddb import SGDBAuthError, SGDBError, SGDBHelper
from src.utils.task import Task


# pylint: disable=too-many-instance-attributes
class Importer:
    """A class in charge of scanning sources for games"""

    progressbar = None
    import_statuspage = None
    import_dialog = None

    sources = None

    n_games_added = 0
    n_source_tasks_created = 0
    n_source_tasks_done = 0
    n_sgdb_tasks_created = 0
    n_sgdb_tasks_done = 0
    sgdb_cancellable = None
    sgdb_error = None

    def __init__(self):
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
            progress = self.n_tasks_done / self.n_tasks_created
        except ZeroDivisionError:
            progress = 1
        return progress

    @property
    def finished(self):
        return self.n_tasks_created == self.n_tasks_done

    def add_source(self, source):
        self.sources.add(source)

    def run(self):
        """Use several Gio.Task to import games from added sources"""

        self.create_dialog()

        # Single SGDB cancellable shared by all its tasks
        # (If SGDB auth is bad, cancel all SGDB tasks)
        self.sgdb_cancellable = Gio.Cancellable()

        for source in self.sources:
            logging.debug("Importing games from source %s", source.id)
            task = Task.new(None, None, self.source_task_callback, (source,))
            self.n_source_tasks_created += 1
            task.set_task_data((source,))
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
            transient_for=shared.win,
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
            if game is None:
                continue

            # TODO register in store instead of dict

            # Avoid duplicates
            if (
                game.game_id in shared.win.games
                and not shared.win.games[game.game_id].removed
            ):
                continue

            # Register game
            logging.info("New game registered %s (%s)", game.name, game.game_id)
            shared.win.games[game.game_id] = game
            game.save()
            self.n_games_added += 1

            # Start sgdb lookup for game
            # HACK move to its own manager
            task = Task.new(
                None, self.sgdb_cancellable, self.sgdb_task_callback, (game,)
            )
            self.n_sgdb_tasks_created += 1
            task.set_task_data((game,))
            task.run_in_thread(self.sgdb_task_thread_func)

    def source_task_callback(self, _obj, _result, data):
        """Source import callback"""
        source, *_rest = data
        logging.debug("Import done for source %s", source.id)
        self.n_source_tasks_done += 1
        self.update_progressbar()
        if self.finished:
            self.import_callback()

    def sgdb_task_thread_func(self, _task, _obj, data, cancellable):
        """SGDB query code"""
        game, *_rest = data
        game.set_loading(1)
        sgdb = SGDBHelper()
        try:
            sgdb.conditionaly_update_cover(game)
        except SGDBAuthError as error:
            cancellable.cancel()
            self.sgdb_error = error
        except (HTTPError, SGDBError) as _error:
            # TODO handle other SGDB errors
            pass

    def sgdb_task_callback(self, _obj, _result, data):
        """SGDB query callback"""
        game, *_rest = data
        logging.debug("SGDB import done for game %s", game.name)
        game.set_loading(-1)
        self.n_sgdb_tasks_done += 1
        self.update_progressbar()
        if self.finished:
            self.import_callback()

    def import_callback(self):
        """Callback called when importing has finished"""
        logging.info("Import done")
        self.import_dialog.close()
        self.create_summary_toast()
        # TODO create a summary of errors/warnings/tips popup (eg. SGDB, Steam libraries)
        if self.sgdb_error is not None:
            self.create_sgdb_error_dialog()

    def create_summary_toast(self):
        """N games imported toast"""

        toast = Adw.Toast()
        toast.set_priority(Adw.ToastPriority.HIGH)

        if self.n_games_added == 0:
            toast.set_title(_("No new games found"))
            toast.set_button_label(_("Preferences"))
            toast.connect(
                "button-clicked",
                self.dialog_response_callback,
                "open_preferences",
                "import",
            )

        elif self.n_games_added == 1:
            toast.set_title(_("1 game imported"))

        elif self.n_games_added > 1:
            # The variable is the number of games
            toast.set_title(_("{} games imported").format(self.n_games_added))

        shared.win.toast_overlay.add_toast(toast)

    def create_sgdb_error_dialog(self):
        """SGDB error dialog"""
        create_dialog(
            shared.win,
            _("Couldn't Connect to SteamGridDB"),
            str(self.sgdb_error),
            "open_preferences",
            _("Preferences"),
        ).connect("response", self.dialog_response_callback, "sgdb")

    def open_preferences(self, page=None, expander_row=None):
        shared.win.get_application().on_preferences_action(
            page_name=page, expander_row=expander_row
        )

    def dialog_response_callback(self, _widget, response, *args):
        """Handle after-import dialogs callback"""
        if response == "open_preferences":
            self.open_preferences(*args)
