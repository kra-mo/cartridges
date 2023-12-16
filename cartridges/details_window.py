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
import shlex
from pathlib import Path
from time import time
from typing import Any, Optional

from gi.repository import Adw, Gio, GLib, Gtk
from PIL import Image, UnidentifiedImageError

from cartridges import shared
from cartridges.errors.friendly_error import FriendlyError
from cartridges.game import Game
from cartridges.game_cover import GameCover
from cartridges.store.managers.cover_manager import CoverManager
from cartridges.store.managers.sgdb_manager import SgdbManager
from cartridges.utils.create_dialog import create_dialog
from cartridges.utils.save_cover import convert_cover, save_cover


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
    file_chooser_button = Gtk.Template.Child()

    apply_button = Gtk.Template.Child()

    cover_changed: bool = False

    def __init__(self, game: Optional[Game] = None, **kwargs: Any):
        super().__init__(**kwargs)

        self.game: Game = game
        self.game_cover: GameCover = GameCover({self.cover})

        self.set_transient_for(shared.win)

        if self.game:
            self.set_title(_("Game Details"))
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
            self.apply_button.set_label(_("Add"))

        image_filter = Gtk.FileFilter(name=_("Images"))
        for extension in Image.registered_extensions():
            image_filter.add_suffix(extension[1:])
            image_filter.add_suffix("svg")  # Gdk.Texture supports .svg but PIL doesn't

        image_filters = Gio.ListStore.new(Gtk.FileFilter)
        image_filters.append(image_filter)

        exec_filter = Gtk.FileFilter(name=_("Executables"))
        exec_filter.add_mime_type("application/x-executable")

        exec_filters = Gio.ListStore.new(Gtk.FileFilter)
        exec_filters.append(exec_filter)

        self.image_file_dialog = Gtk.FileDialog()
        self.image_file_dialog.set_filters(image_filters)
        self.image_file_dialog.set_default_filter(image_filter)

        self.exec_file_dialog = Gtk.FileDialog()
        self.exec_file_dialog.set_filters(exec_filters)
        self.exec_file_dialog.set_default_filter(exec_filter)

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

        self.exec_info_popover.update_property(
            (Gtk.AccessibleProperty.LABEL,),
            (
                exec_info_text.replace("<tt>", "").replace("</tt>", ""),
            ),  # Remove formatting, else the screen reader reads it
        )

        def set_exec_info_a11y_label(*_args: Any) -> None:
            self.set_focus(self.exec_info_popover)

        self.exec_info_popover.connect("show", set_exec_info_a11y_label)

        self.cover_button_delete.connect("clicked", self.delete_pixbuf)
        self.cover_button_edit.connect("clicked", self.choose_cover)
        self.file_chooser_button.connect("clicked", self.choose_executable)
        self.apply_button.connect("clicked", self.apply_preferences)

        self.name.connect("entry-activated", self.focus_executable)
        self.developer.connect("entry-activated", self.focus_executable)
        self.executable.connect("entry-activated", self.apply_preferences)

        self.set_focus(self.name)
        self.present()

    def delete_pixbuf(self, *_args: Any) -> None:
        self.game_cover.new_cover()

        self.cover_button_delete_revealer.set_reveal_child(False)
        self.cover_changed = True

    def apply_preferences(self, *_args: Any) -> None:
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
            source_id = "imported"
            numbers = [0]
            game_id: str
            for game_id in shared.store.source_games.get(source_id, set()):
                prefix = "imported_"
                if not game_id.startswith(prefix):
                    continue
                numbers.append(int(game_id.replace(prefix, "", 1)))

            game_number = max(numbers) + 1

            self.game = Game(
                {
                    "game_id": f"imported_{game_number}",
                    "hidden": False,
                    "source": source_id,
                    "added": int(time()),
                }
            )

            if shared.win.sidebar.get_selected_row().get_child() not in (
                shared.win.all_games_row_box,
                shared.win.added_row_box,
            ):
                shared.win.sidebar.select_row(shared.win.added_row_box.get_parent())

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

        if self.game.game_id in shared.win.game_covers.keys():
            shared.win.game_covers[self.game.game_id].animation = None

        shared.win.game_covers[self.game.game_id] = self.game_cover

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
            sgdb_manager = shared.store.managers[SgdbManager]
            sgdb_manager.reset_cancellable()
            sgdb_manager.process_game(self.game, {}, self.update_cover_callback)

        self.game_cover.pictures.remove(self.cover)

        self.close()
        shared.win.show_details_page(self.game)

    def update_cover_callback(self, manager: SgdbManager) -> None:
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

    def update_cover_error_response(self, _widget: Any, response: str) -> None:
        if response == "open_preferences":
            shared.win.get_application().on_preferences_action(page_name="sgdb")

    def focus_executable(self, *_args: Any) -> None:
        self.set_focus(self.executable)

    def toggle_loading(self) -> None:
        self.apply_button.set_sensitive(not self.apply_button.get_sensitive())
        self.spinner.set_spinning(not self.spinner.get_spinning())
        self.cover_overlay.set_opacity(not self.cover_overlay.get_opacity())

    def set_cover(self, _source: Any, result: Gio.Task, *_args: Any) -> None:
        try:
            path = self.image_file_dialog.open_finish(result).get_path()
        except GLib.Error:
            return

        def thread_func() -> None:
            new_path = None

            try:
                with Image.open(path) as image:
                    if getattr(image, "is_animated", False):
                        new_path = convert_cover(path)
            except UnidentifiedImageError:
                pass

            if not new_path:
                new_path = convert_cover(
                    pixbuf=shared.store.managers[CoverManager].composite_cover(
                        Path(path)
                    )
                )

            if new_path:
                self.game_cover.new_cover(new_path)
                self.cover_button_delete_revealer.set_reveal_child(True)
                self.cover_changed = True

            self.toggle_loading()

        self.toggle_loading()
        GLib.Thread.new(None, thread_func)

    def set_executable(self, _source: Any, result: Gio.Task, *_args: Any) -> None:
        try:
            path = self.exec_file_dialog.open_finish(result).get_path()
        except GLib.Error:
            return

        self.executable.set_text(shlex.quote(path))

    def choose_executable(self, *_args: Any) -> None:
        self.exec_file_dialog.open(self, None, self.set_executable)

    def choose_cover(self, *_args: Any) -> None:
        self.image_file_dialog.open(self, None, self.set_cover)
