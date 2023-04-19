# importer.py
#
# Copyright 2022-2023 kramo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from gi.repository import Adw, Gtk

from .create_dialog import create_dialog
from .game import Game
from .save_cover import resize_cover, save_cover
from .steamgriddb import SGDBSave, needs_cover


class Importer:
    def __init__(self, win):
        self.win = win
        self.total_queue = 0
        self.queue = 0
        self.games_no = 0
        self.blocker = False
        self.games = set()
        self.sgdb_exception = None

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
            transient_for=win,
            deletable=False,
        )

        self.import_dialog.present()

    def save_game(self, values=None, cover_path=None):
        if values:
            game = Game(self.win, values)

            if not needs_cover(self.win.schema, cover_path):
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

    def done(self):
        self.update_progressbar()
        if self.queue == 0:
            self.import_dialog.close()

            if self.games_no == 0:
                create_dialog(
                    self.win,
                    _("No Games Found"),
                    _("No new games were found on your system."),
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", self.response, "import")

            elif self.games_no == 1:
                create_dialog(
                    self.win,
                    _("Game Imported"),
                    _("Successfully imported 1 game."),
                ).connect("response", self.response, "import")
            elif self.games_no > 1:
                games_no = self.games_no
                create_dialog(
                    self.win,
                    _("Games Imported"),
                    # The variable is the number of games
                    _("Successfully imported {} games.").format(games_no),
                ).connect("response", self.response, "import")

    def response(self, _widget, response, page_name=None, expander_row=None):
        if response == "open_preferences":
            self.win.get_application().on_preferences_action(
                None, page_name=page_name, expander_row=expander_row
            )
        elif self.sgdb_exception:
            create_dialog(
                self.win,
                _("Couldn't Connect to SteamGridDB"),
                self.sgdb_exception,
                "open_preferences",
                _("Preferences"),
            ).connect("response", self.response, "sgdb")
            self.sgdb_exception = None
        elif (
            self.win.schema.get_boolean("steam")
            and self.win.schema.get_boolean("steam-extra-dirs-hint")
            and not self.win.schema.get_strv("steam-extra-dirs")
        ):
            steam_library_path = (
                Path(self.win.schema.get_string("steam-location"))
                / "steamapps"
                / "libraryfolders.vdf"
            )
            if (
                steam_library_path.exists()
                and steam_library_path.read_text("utf-8").count('"path"') > 1
            ):
                self.win.schema.set_boolean("steam-extra-dirs-hint", False)
                create_dialog(
                    self.win,
                    _("Extra Steam Libraries"),
                    _(
                        "Looks like you have multiple Steam libraries. Would you like to add them in preferences?"
                    ),
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", self.response, "import", "steam_expander_row")

    def update_progressbar(self):
        try:
            self.progressbar.set_fraction(1 - (self.queue / self.total_queue))
        except ZeroDivisionError:
            self.progressbar.set_fraction(1)
