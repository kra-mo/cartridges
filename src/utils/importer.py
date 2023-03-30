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

from gi.repository import Adw, Gtk

from .create_dialog import create_dialog
from .save_cover import save_cover
from .save_game import save_game


class Importer:
    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
        self.total_queue = 0
        self.queue = 0
        self.games_no = 0
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
            self.games_no += 1
            save_game(values)
            self.parent_widget.update_games([values["game_id"]])
            if "blacklisted" in values.keys():
                self.games_no -= 1

        self.queue -= 1
        self.progressbar.set_fraction(1 - (self.queue / self.total_queue))

        if self.queue == 0 and not self.blocker:
            self.import_dialog.close()

            def response(_widget, response):
                if response == "open_preferences":
                    self.parent_widget.get_application().on_preferences_action(
                        None, page_name="import"
                    )

            if self.games_no == 0:
                create_dialog(
                    self.parent_widget,
                    _("No Games Found"),
                    _("No new games were found on your system."),
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", response)

            elif self.games_no == 1:
                create_dialog(
                    self.parent_widget,
                    _("Game Imported"),
                    _("Successfully imported 1 game."),
                )
            elif self.games_no > 1:
                games_no = self.games_no
                create_dialog(
                    self.parent_widget,
                    _("Games Imported"),
                    # The variable is the number of games
                    _(f"Successfully imported {games_no} games."),
                )
