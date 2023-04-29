from gi.repository import Adw, Gtk, Gio

class Importer():

    # Display values
    win = None
    progressbar = None
    import_statuspage = None
    import_dialog = None

    # Importer values
    count_total = 0
    count_done = 0
    sources = list()

    def __init__(self, win) -> None:
        self.win = win

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

    def get_progress(self):
        """Get the current progression as a number between 0 and 1"""
        progress = 1
        if self.total_queue > 0:
            progress = 1 - self.queue / self.total_queue
        return progress

    def update_progressbar(self):
        """Update the progress bar"""
        progress = self.get_progress()
        self.progressbar.set_fraction(progress)

    def add_source(self, source):
        """Add a source to import games from"""
        self.sources.append(source)

    def import_games(self):
        """Import games from the specified sources"""
        self.create_dialog()

        # TODO make that async, you doofus
        # Every source does its job on the side, informing of the amount of work and when a game is done.
        # At the end of the task, it returns the games.

        # Idea 1 - Work stealing queue
        # 1. Sources added to the queue
        # 2. Worker A takes source X and advances it
        # 3. Worker A puts back source X to the queue
        # 4. Worker B takes source X, that has ended
        # 5. Worker B doesn't add source X back to the queue

        # Idea 2 - Gio.Task
        # 1. A task is created for every source
        # 2. Source X finishes
        # 3. Importer adds the games

        for source in self.sources:
            for game in source:
                game.save()

        self.close_dialog()