import logging
from pathlib import Path
from threading import Lock, Thread

import requests
from requests import HTTPError
from gi.repository import Adw, Gio, Gtk

from .save_cover import resize_cover, save_cover
from .steamgriddb import SGDBHelper, SGDBError


class Importer:
    """A class in charge of scanning sources for games"""

    # Dialog widget
    progressbar = None
    import_statuspage = None
    import_dialog = None

    # Caller-set values
    win = None
    sources = None

    # Internal values
    source_threads = None
    sgdb_threads = None
    progress_lock = None
    games_lock = None
    sgdb_threads_lock = None
    counts = None
    games = None

    def __init__(self, win):
        self.games = set()
        self.sources = set()
        self.counts = {}
        self.source_threads = []
        self.sgdb_threads = []
        self.games_lock = Lock()
        self.progress_lock = Lock()
        self.sgdb_threads_lock = Lock()
        self.win = win

    @property
    def progress(self):
        # Compute overall values
        overall = {"games": 0, "covers": 0, "total": 0}
        with self.progress_lock:
            for source in self.sources:
                for key in overall:
                    overall[key] = self.counts[source.id][key]
        # Compute progress
        try:
            progress = 1 - (overall["games"] + overall["covers"]) / overall["total"] * 2
        except ZeroDivisionError:
            progress = 1
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
        self.counts[source.id] = {"games": 0, "covers": 0, "total": 0}

    def run_in_thread(self):
        thread = ImporterThread(self, self.win)
        thread.start()


class ImporterThread(Thread):
    """Thread in charge of the import process"""

    importer = None
    win = None

    def __init__(self, importer, win, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.importer = importer
        self.win = win

    def run(self):
        """Thread entry point"""

        self.importer.create_dialog()

        # Scan sources in threads
        for source in self.importer.sources:
            print(f"{source.full_name}, installed: {source.is_installed}")
            if not source.is_installed:
                continue
            thread = SourceThread(source, self.win, self.importer)
            self.importer.source_threads.append(thread)
            thread.start()

        for thread in self.importer.source_threads:
            thread.join()

        # Save games
        for game in self.importer.games:
            if (
                game.game_id in self.win.games
                and not self.win.games[game.game_id].removed
            ):
                continue
            game.save()

        # Wait for SGDB query threads to finish
        for thread in self.importer.sgdb_threads:
            thread.join()

        self.importer.import_dialog.close()


class SourceThread(Thread):
    """Thread in charge of scanning a source for games"""

    source = None
    win = None
    importer = None

    def __init__(self, source, win, importer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.source = source
        self.win = win
        self.importer = importer

    def run(self):
        """Thread entry point"""

        # Initialize source iteration
        iterator = iter(self.source)
        with self.importer.progress_lock:
            self.importer.counts[self.source.id]["total"] = len(iterator)

        # Get games from source
        while True:
            # Handle exceptions raised while iteration the source
            try:
                game = next(iterator)
            except StopIteration:
                break
            except Exception as exception:  # pylint: disable=broad-exception-caught
                logging.exception(
                    msg=f"Exception in source {self.source.id}",
                    exc_info=exception,
                )
                continue

            # Add game to importer
            with self.importer.games_lock:
                self.importer.games.add(game)
            with self.importer.progress_lock:
                self.importer.counts[self.source.id]["games"] += 1
            self.importer.update_progressbar()

            # Start sgdb lookup for game in another thread
            # HACK move to a game manager
            use_sgdb = self.win.schema.get_boolean("sgdb")
            if use_sgdb and not game.blacklisted:
                sgdb_thread = SGDBThread(game, self.win, self.importer)
                with self.importer.sgdb_threads_lock:
                    self.importer.sgdb_threads.append(sgdb_thread)
                sgdb_thread.start()


class SGDBThread(Thread):
    """Thread in charge of querying SGDB for a game image"""

    game = None
    win = None
    importer = None

    def __init__(self, game, win, importer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        self.win = win
        self.importer = importer

    def run(self):
        """Thread entry point"""

        # Check if we should query SGDB
        prefer_sgdb = self.win.schema.get_boolean("sgdb-prefer")
        prefer_animated = self.win.schema.get_boolean("sgdb-animated")
        image_trunk = self.win.covers_dir / self.game.game_id
        still = image_trunk.with_suffix(".tiff")
        animated = image_trunk.with_suffix(".gif")

        # Breaking down the condition
        is_missing = not still.is_file() and not animated.is_file()
        is_not_best = not animated.is_file() and prefer_animated
        if not (is_missing or is_not_best or prefer_sgdb):
            return

        self.game.set_loading(1)

        # Add image from sgdb
        sgdb = SGDBHelper(self.win)
        try:
            sgdb_id = sgdb.get_game_id(self.game)
            uri = sgdb.get_game_image_uri(sgdb_id, animated=prefer_animated)
            response = requests.get(uri, timeout=5)
        except HTTPError as _error:
            # TODO handle http errors
            pass
        except SGDBError as _error:
            # TODO handle SGDB API errors
            pass
        else:
            tmp_file = Gio.File.new_tmp()[0]
            tmp_file_path = tmp_file.get_path()
            Path(tmp_file_path).write_bytes(response.content)
            save_cover(
                self.win, self.game.game_id, resize_cover(self.win, tmp_file_path)
            )

        self.game.set_loading(0)
        with self.importer.progress_lock:
            self.importer.counts[self.game.source.id]["covers"] += 1
