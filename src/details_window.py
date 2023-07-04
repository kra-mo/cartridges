# details_window.py
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

import os
from time import time

from gi.repository import Adw, Gio, GLib, Gtk
from PIL import Image

from src import shared
from src.errors.friendly_error import FriendlyError
from src.game import Game
from src.game_cover import GameCover
from src.store.managers.sgdb_manager import SGDBManager
from src.utils.create_dialog import create_dialog
from src.utils.save_cover import resize_cover, save_cover


@Gtk.Template(resource_path=shared.PREFIX + "/gtk/details-window.ui")
class DetailsWindow(Adw.Window):
    __gtype_name__ = "DetailsWindow"

    cover_overlay = Gtk.Template.Child()
    cover = Gtk.Template.Child()
    cover_button_edit = Gtk.Template.Child()
    cover_button_delete_revealer = Gtk.Template.Child()
    cover_button_delete = Gtk.Template.Child()
    spinner = Gtk.Template.Child()

    name = Gtk.Template.Child()
    developer = Gtk.Template.Child()
    executable = Gtk.Template.Child()

    exec_info_label = Gtk.Template.Child()
    exec_info_popover = Gtk.Template.Child()

    apply_button = Gtk.Template.Child()

    cover_changed = False

    def __init__(self, game=None, **kwargs):
        super().__init__(**kwargs)

        self.win = shared.win
        self.game = game
        self.game_cover = GameCover({self.cover})

        self.set_transient_for(self.win)

        if self.game:
            self.set_title(_("Edit Game Details"))
            self.name.set_text(self.game.name)
            if self.game.developer:
                self.developer.set_text(self.game.developer)
            self.executable.set_text(self.game.executable)
            self.apply_button.set_label(_("Apply"))

            self.game_cover.new_cover(self.game.get_cover_path())
            if self.game_cover.get_texture():
                self.cover_button_delete_revealer.set_reveal_child(True)
        else:
            self.set_title(_("Add New Game"))
            self.apply_button.set_label(_("Confirm"))

        image_filter = Gtk.FileFilter(name=_("Images"))
        for extension in Image.registered_extensions():
            image_filter.add_suffix(extension[1:])

        file_filters = Gio.ListStore.new(Gtk.FileFilter)
        file_filters.append(image_filter)
        self.file_dialog = Gtk.FileDialog()
        self.file_dialog.set_filters(file_filters)

        # Translate this string as you would translate "file"
        file_name = _("file.txt")
        # As in software
        exe_name = _("program")

        if os.name == "nt":
            exe_name += ".exe"
            # Translate this string as you would translate "path to {}"
            exe_path = _("C:\\path\\to\\{}").format(exe_name)
            # Translate this string as you would translate "path to {}"
            file_path = _("C:\\path\\to\\{}").format(file_name)
            command = "start"
        else:
            # Translate this string as you would translate "path to {}"
            exe_path = _("/path/to/{}").format(exe_name)
            # Translate this string as you would translate "path to {}"
            file_path = _("/path/to/{}").format(file_name)
            command = "xdg-open"

        # pylint: disable=line-too-long
        exec_info_text = _(
            'To launch the executable "{}", use the command:\n\n<tt>"{}"</tt>\n\nTo open the file "{}" with the default application, use:\n\n<tt>{} "{}"</tt>\n\nIf the path contains spaces, make sure to wrap it in double quotes!'
        ).format(exe_name, exe_path, file_name, command, file_path)

        self.exec_info_label.set_label(exec_info_text)

        def clear_info_selection(*_args):
            self.exec_info_label.select_region(-1, -1)

        self.exec_info_popover.connect("show", clear_info_selection)

        self.cover_button_delete.connect("clicked", self.delete_pixbuf)
        self.cover_button_edit.connect("clicked", self.choose_cover)
        self.apply_button.connect("clicked", self.apply_preferences)

        self.name.connect("activate", self.focus_executable)
        self.developer.connect("activate", self.focus_executable)
        self.executable.connect("activate", self.apply_preferences)

        self.set_focus(self.name)
        self.present()

    def delete_pixbuf(self, *_args):
        self.game_cover.new_cover()

        self.cover_button_delete_revealer.set_reveal_child(False)
        self.cover_changed = True

    def apply_preferences(self, *_args):
        final_name = self.name.get_text()
        final_developer = self.developer.get_text()
        final_executable = self.executable.get_text()

        if not self.game:
            if final_name == "":
                create_dialog(
                    self, _("Couldn't Add Game"), _("Game title cannot be empty.")
                )
                return

            if final_executable == "":
                create_dialog(
                    self, _("Couldn't Add Game"), _("Executable cannot be empty.")
                )
                return

            # Increment the number after the game id (eg. imported_1, imported_2)
            numbers = [0]
            game_id: str
            for game_id in shared.store.games:
                prefix = "imported_"
                if not game_id.startswith(prefix):
                    continue
                numbers.append(int(game_id.replace(prefix, "", 1)))
            game_number = max(numbers) + 1

            self.game = Game(
                {
                    "game_id": f"imported_{game_number}",
                    "hidden": False,
                    "source": "imported",
                    "added": int(time()),
                }
            )

        else:
            if final_name == "":
                create_dialog(
                    self,
                    _("Couldn't Apply Preferences"),
                    _("Game title cannot be empty."),
                )
                return

            if final_executable == "":
                create_dialog(
                    self,
                    _("Couldn't Apply Preferences"),
                    _("Executable cannot be empty."),
                )
                return

        self.game.name = final_name
        self.game.developer = final_developer or None
        self.game.executable = final_executable

        if self.game.game_id in self.win.game_covers.keys():
            self.win.game_covers[self.game.game_id].animation = None

        self.win.game_covers[self.game.game_id] = self.game_cover

        if self.cover_changed:
            save_cover(
                self.game.game_id,
                self.game_cover.path,
            )

        shared.store.add_game(self.game, {}, run_pipeline=False)
        self.game.save()
        self.game.update()

        # TODO: this is fucked up (less than before)
        # Get a cover from SGDB if none is present
        if not self.game_cover.get_texture():
            self.game.set_loading(1)
            sgdb_manager: SGDBManager = shared.store.managers[SGDBManager]
            sgdb_manager.reset_cancellable()
            sgdb_manager.process_game(self.game, {}, self.update_cover_callback)

        self.game_cover.pictures.remove(self.cover)

        self.close()
        self.win.show_details_page(self.game)

    def update_cover_callback(self, manager: SGDBManager):
        # Set the game as not loading
        self.game.set_loading(-1)
        self.game.update()

        # Handle errors that occured
        for error in manager.collect_errors():
            # On auth error, inform the user
            if isinstance(error, FriendlyError):
                create_dialog(
                    shared.win,
                    error.title,
                    error.subtitle,
                    "open_preferences",
                    _("Preferences"),
                ).connect("response", self.update_cover_error_response)

    def update_cover_error_response(self, _widget, response):
        if response == "open_preferences":
            shared.win.get_application().on_preferences_action(page_name="sgdb")

    def focus_executable(self, *_args):
        self.set_focus(self.executable)

    def toggle_loading(self):
        self.apply_button.set_sensitive(not self.apply_button.get_sensitive())
        self.spinner.set_spinning(not self.spinner.get_spinning())
        self.cover_overlay.set_opacity(not self.cover_overlay.get_opacity())

    def set_cover(self, _source, result, *_args):
        try:
            path = self.file_dialog.open_finish(result).get_path()
        except GLib.GError:
            return

        def resize():
            if cover := resize_cover(path):
                self.game_cover.new_cover(cover)
                self.cover_button_delete_revealer.set_reveal_child(True)
                self.cover_changed = True
            self.toggle_loading()

        self.toggle_loading()
        GLib.Thread.new(None, resize)

    def choose_cover(self, *_args):
        self.file_dialog.open(self, None, self.set_cover)
