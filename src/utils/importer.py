from gi.repository import Adw, Gtk

from .create_dialog import create_dialog
from .save_cover import save_cover
from .save_game import save_game


class Importer:
    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
        self.total_queue = 0
        self.queue = 0
        self.imported_no = 0
        self.blocker = False

        self.progressbar = Gtk.ProgressBar(margin_start=12, margin_end=12)
        import_statuspage = Adw.StatusPage(
            title=_("Importing Games…"),
            child=self.progressbar,
        )
        self.import_dialog = Adw.Window(
            content=import_statuspage,
            modal=True,
            default_width=350,
            default_height=-1,
            transient_for=parent_widget,
            deletable=False,
        )

        self.import_dialog.present()

    def save_cover(self, game_id, cover_path):
        save_cover(self.parent_widget, game_id, cover_path)

    def save_game(self, values=None):
        if values:
            self.imported_no += 1
            save_game(values)
            self.parent_widget.update_games([values["game_id"]])

        self.queue -= 1
        self.progressbar.set_fraction(1 - (self.queue / self.total_queue))

        if self.queue == 0 and not self.blocker:
            self.import_dialog.close()

            def response(_widget, response):
                if response == "open_preferences":
                    self.parent_widget.get_application().on_preferences_action(None)

            if self.imported_no == 0:
                create_dialog(
                    self.parent_widget,
                    _("No Games Found"),
                    _("No new games were found on your device."),
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", response)

            elif self.imported_no == 1:
                create_dialog(
                    self.parent_widget,
                    _("Game Imported"),
                    _("Successfully imported 1 game."),
                )
            elif self.imported_no > 1:
                create_dialog(
                    self.parent_widget,
                    _("Games Imported"),
                    # The variable is the number of games
                    _(f"Successfully imported {self.imported_no} games."),
                )
