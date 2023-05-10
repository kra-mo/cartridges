import logging
from pathlib import Path
from threading import Lock, Thread


import requests
from gi.repository import Adw, Gio, Gtk

from .save_cover import resize_cover, save_cover
from .steamgriddb import SGDBHelper


class Importer:
    win = None
    progressbar = None
    import_statuspage = None
    import_dialog = None
    sources = None

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

    def import_games(self):
        self.create_dialog()

        # Scan sources in threads
        for source in self.sources:
            print(f"{source.full_name}, installed: {source.is_installed}")
            if not source.is_installed:
                continue
            thread = Thread(target=self.__import_source__, args=tuple([source]))  # fmt: skip
            self.source_threads.append(thread)
            thread.start()

        for thread in self.source_threads:
            thread.join()

        # Save games
        for game in self.games:
            if (
                game.game_id in self.win.games
                and not self.win.games[game.game_id].removed
            ):
                continue
            game.save()

        # Wait for SGDB image import to finish
        for thread in self.sgdb_threads:
            thread.join()

        self.import_dialog.close()

    def __import_source__(self, *args, **_kwargs):
        """Source import thread entry point"""
        source, *_rest = args

        # Initialize source iteration
        iterator = source.__iter__()
        with self.progress_lock:
            self.counts[source.id]["total"] = len(iterator)

        # Handle iteration exceptions
        def wrapper(iterator):
            while True:
                try:
                    yield next(iterator)
                except StopIteration:
                    break
                except Exception as exception:  # pylint: disable=broad-exception-caught
                    logging.exception(
                        msg=f"Exception in source {iterator.source.id}",
                        exc_info=exception,
                    )
                    continue

        # Get games from source
        for game in wrapper(iterator):
            with self.games_lock:
                self.games.add(game)
            with self.progress_lock:
                self.counts[source.id]["games"] += 1
            self.update_progressbar()

            # Start sgdb lookup for game
            # HACK move to a game manager
            sgdb_thread = Thread(target=self.__sgdb_lookup__, args=tuple([game]))
            with self.sgdb_threads_lock:
                self.sgdb_threads.append(sgdb_thread)
            sgdb_thread.start()

    def __sgdb_lookup__(self, *args, **_kwargs):
        """SGDB lookup thread entry point"""
        game, *_rest = args

        def inner():
            # Skip obvious ones
            if game.blacklisted:
                return
            use_sgdb = self.win.schema.get_boolean("sgdb")
            if not use_sgdb:
                return
            # Check if we should query SGDB
            prefer_sgdb = self.win.schema.get_boolean("sgdb-prefer")
            prefer_animated = self.win.schema.get_boolean("sgdb-animated")
            image_trunk = self.win.covers_dir / game.game_id
            still = image_trunk.with_suffix(".tiff")
            animated = image_trunk.with_suffix(".gif")
            # breaking down the condition
            is_missing = not still.is_file() and not animated.is_file()
            is_not_best = not animated.is_file() and prefer_animated
            should_query = is_missing or is_not_best or prefer_sgdb
            if not should_query:
                return
            # Add image from sgdb
            game.set_loading(1)
            sgdb = SGDBHelper(self.win)
            uri = sgdb.get_game_image_uri(game, animated=prefer_animated)
            response = requests.get(uri, timeout=5)
            tmp_file = Gio.File.new_tmp()[0]
            tmp_file_path = tmp_file.get_path()
            Path(tmp_file_path).write_bytes(response.content)
            save_cover(self.win, game.game_id, resize_cover(self.win, tmp_file_path))
            game.set_loading(0)

        try:
            inner()
        except Exception:  # pylint: disable=broad-exception-caught
            # TODO for god's sake handle exceptions correctly
            # TODO (talk about that with Kramo)
            pass
        with self.progress_lock:
            self.counts[game.source]["covers"] += 1
