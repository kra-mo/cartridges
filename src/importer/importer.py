from threading import Thread, Lock
from gi.repository import Adw, Gtk, Gio

from .game import Game
from .steamgriddb import SGDBSave


class Importer:
    win = None
    progressbar = None
    import_statuspage = None
    import_dialog = None
    sources = None

    progress_lock = None
    counts = None

    games_lock = None
    games = None

    def __init__(self, win) -> None:
        self.games = set()
        self.sources = list()
        self.counts = dict()
        self.games_lock = Lock()
        self.progress_lock = Lock()
        self.win = win

    @property
    def progress(self):
        # Compute overall values
        done = 0
        total = 0
        for source in self.sources:
            done += self.counts[source.id]["done"]
            total += self.counts[source.id]["total"]
        # Compute progress
        progress = 1
        if total > 0:
            progress = 1 - done / total
        return progress

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

    def close_dialog(self):
        """Close the import dialog"""
        self.import_dialog.close()

    def update_progressbar(self):
        """Update the progress bar"""
        progress = self.progress()
        self.progressbar.set_fraction(progress)

    def add_source(self, source):
        """Add a source to import games from"""
        self.sources.append(source)
        self.counts[source.id] = {"done": 0, "total": 0}

    def import_games(self):
        """Import games from the specified sources"""

        self.create_dialog()

        # Scan all sources
        threads = []
        for source in self.sources:
            t = Thread(
                None,
                self.__import_from_source,
                args=tuple(
                    source,
                ),
            )
            threads.append(t)
            t.start()

        # Wait for all of them to finish
        for t in threads:
            t.join()

        self.close_dialog()

    def __import_from_source(self, *args, **kwargs):
        """Source import thread entry point"""
        # TODO just get Game objects from the sources
        source, *rest = args

        iterator = source.__iter__()
        for game_values in iterator:
            game = Game(self.win, game_values)

            self.games_lock.acquire()
            self.games.add(game)
            self.games_lock.release()

            self.progress_lock.acquire()
            self.counts[source.id]["total"] = len(iterator)
            if not game.blacklisted:
                self.counts[source.id]["done"] += 1
            self.update_progressbar()
            self.progress_lock.release()

    # TODO remove after not needed
    def save_game(self, values=None, cover_path=None):
        if values:
            game = Game(self.win, values)

            if save_cover:
                save_cover(self.win, game.game_id, resize_cover(self.win, cover_path))

            self.games.add(game)

            self.games_no += 1
            if game.blacklisted:
                self.games_no -= 1

        self.queue -= 1
        self.update_progressbar()

        if self.queue == 0 and not self.blocker:
            if self.games:
                self.total_queue = len(self.games)
                self.queue = len(self.games)
                self.import_statuspage.set_title(_("Importing Covers…"))
                self.update_progressbar()
                SGDBSave(self.win, self.games, self)
            else:
                self.done()