from threading import Thread, Lock
from gi.repository import Adw, Gtk, Gio

from .game import Game
from .steamgriddb import SGDBHelper


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
        self.sources = set()
        self.counts = dict()
        self.games_lock = Lock()
        self.progress_lock = Lock()
        self.win = win

    @property
    def progress(self):
        # Compute overall values
        done = 0
        total = 0
        with self.progress_lock:
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
        self.import_dialog.close()

    def update_progressbar(self):
        self.progressbar.set_fraction(self.progress)

    def add_source(self, source):
        self.sources.add(source)
        self.counts[source.id] = {"done": 0, "total": 0}

    def import_games(self):
        self.create_dialog()

        # Scan sources in threads
        threads = []
        for source in self.sources:
            print(f"{source.full_name}, installed: {source.is_installed}")  # ! DEBUG
            if not source.is_installed:
                continue
            t = Thread(target=self.__import_source, args=tuple([source]))  # fmt: skip
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Save games
        for game in self.games:
            game.save()

        self.close_dialog()

    def __import_source(self, *args, **kwargs):
        """Source import thread entry point"""
        # TODO error handling in source iteration
        # TODO add SGDB image (move to a game manager)
        source, *rest = args
        iterator = source.__iter__()
        with self.progress_lock:
            self.counts[source.id]["total"] = iterator.__len__()
        for game in iterator:
            with self.games_lock:
                self.games.add(game)
            with self.progress_lock:
                if not game.blacklisted:
                    self.counts[source.id]["done"] += 1
            self.update_progressbar()
