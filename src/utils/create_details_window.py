# create_details_window.py
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

import json
import os
import shlex
import time

from gi.repository import Adw, GdkPixbuf, Gio, GLib, GObject, Gtk

from .create_dialog import create_dialog
from .save_cover import save_cover
from .save_game import save_game
from .steamgriddb import SGDBSave


def create_details_window(parent_widget, game_id=None):
    window = Adw.Window(
        modal=True, default_width=500, default_height=-1, transient_for=parent_widget
    )

    games = parent_widget.games
    pixbuf = None
    cover_deleted = False

    cover_button_edit = Gtk.Button(
        icon_name="document-edit-symbolic",
        halign=Gtk.Align.END,
        valign=Gtk.Align.END,
        margin_bottom=6,
        margin_end=6,
        css_classes=["circular", "osd"],
    )

    cover_button_delete = Gtk.Button(
        icon_name="user-trash-symbolic",
        css_classes=["circular", "osd"],
        halign=Gtk.Align.END,
        valign=Gtk.Align.END,
        margin_bottom=6,
        margin_end=6,
    )

    def delete_pixbuf(_widget):
        nonlocal pixbuf
        nonlocal cover_deleted

        cover.set_pixbuf(parent_widget.placeholder_pixbuf)
        cover_button_delete_revealer.set_reveal_child(False)
        pixbuf = None
        cover_deleted = True

    cover_button_delete.connect("clicked", delete_pixbuf)

    cover_button_delete_revealer = Gtk.Revealer(
        child=cover_button_delete,
        transition_type=Gtk.RevealerTransitionType.CROSSFADE,
        margin_end=40,
    )

    if not game_id:
        window.set_title(_("Add New Game"))
        cover = Gtk.Picture.new_for_pixbuf(parent_widget.placeholder_pixbuf)
        name = Gtk.Entry()
        developer = Gtk.Entry()
        executable = Gtk.Entry()
        apply_button = Gtk.Button.new_with_label(_("Confirm"))
    else:
        window.set_title(_("Edit Game Details"))
        cover = Gtk.Picture.new_for_pixbuf(parent_widget.games[game_id].pixbuf)
        developer = Gtk.Entry.new_with_buffer(
            Gtk.EntryBuffer.new(games[game_id].developer, -1)
        )
        name = Gtk.Entry.new_with_buffer(Gtk.EntryBuffer.new(games[game_id].name, -1))
        executable = Gtk.Entry.new_with_buffer(
            Gtk.EntryBuffer.new(shlex.join(games[game_id].executable), -1)
        )
        apply_button = Gtk.Button.new_with_label(_("Apply"))

        if parent_widget.games[game_id].pixbuf != parent_widget.placeholder_pixbuf:
            cover_button_delete_revealer.set_reveal_child(True)

    image_filter = Gtk.FileFilter(name=_("Images"))
    image_filter.add_pixbuf_formats()
    file_filters = Gio.ListStore.new(Gtk.FileFilter)
    file_filters.append(image_filter)
    filechooser = Gtk.FileDialog()
    filechooser.set_filters(file_filters)

    cover.add_css_class("card")
    cover.set_size_request(200, 300)

    cover_overlay = Gtk.Overlay(
        child=cover,
        halign=Gtk.Align.CENTER,
        valign=Gtk.Align.CENTER,
    )

    cover_overlay.add_overlay(cover_button_edit)
    cover_overlay.add_overlay(cover_button_delete_revealer)

    cover_clamp = Adw.Clamp(
        maximum_size=200,
        child=cover_overlay,
    )

    cover_group = Adw.PreferencesGroup()
    cover_group.add(cover_clamp)

    title_group = Adw.PreferencesGroup(
        title=_("Title"),
        description=_("The title of the game"),
    )
    title_group.add(name)

    developer_group = Adw.PreferencesGroup(
        title=_("Developer"),
        description=_("The developer or publisher (optional)"),
    )
    developer_group.add(developer)

    exec_info_button = Gtk.ToggleButton(
        icon_name="dialog-information-symbolic",
        valign=Gtk.Align.CENTER,
        css_classes=["flat", "circular"],
    )

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

    exec_info_text = _(
        'To launch the executable "{}", use the command:\n\n<tt>"{}"</tt>\n\nTo open the file "{}" with the default application, use:\n\n<tt>{} "{}"</tt>\n\nIf the path contains spaces, make sure to wrap it in double quotes!'
    ).format(exe_name, exe_path, file_name, command, file_path)

    exec_info_label = Gtk.Label(
        label=exec_info_text,
        use_markup=True,
        wrap=True,
        max_width_chars=30,
        margin_top=6,
        margin_bottom=12,
        margin_start=6,
        margin_end=6,
    )

    exec_info_popover = Gtk.Popover(
        position=Gtk.PositionType.TOP, child=exec_info_label
    )

    exec_info_popover.bind_property(
        "visible", exec_info_button, "active", GObject.BindingFlags.BIDIRECTIONAL
    )

    exec_group = Adw.PreferencesGroup(
        title=_("Executable"),
        description=_("File to open or command to run when launching the game"),
        header_suffix=exec_info_button,
    )
    exec_info_popover.set_parent(exec_group.get_header_suffix())
    exec_group.add(executable)

    general_page = Adw.PreferencesPage(vexpand=True)
    general_page.add(cover_group)
    general_page.add(title_group)
    general_page.add(developer_group)
    general_page.add(exec_group)

    cancel_button = Gtk.Button.new_with_label(_("Cancel"))

    apply_button.add_css_class("suggested-action")

    header_bar = Adw.HeaderBar(
        show_start_title_buttons=False,
        show_end_title_buttons=False,
    )
    header_bar.pack_start(cancel_button)
    header_bar.pack_end(apply_button)

    main_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    main_box.append(header_bar)
    main_box.append(general_page)
    window.set_content(main_box)

    def choose_cover(_widget):
        filechooser.open(window, None, set_cover, None)

    def set_cover(_source, result, _unused):
        nonlocal pixbuf
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                filechooser.open_finish(result).get_path(), 200, 300, False
            )
            cover_button_delete_revealer.set_reveal_child(True)
            cover.set_pixbuf(pixbuf)
        except GLib.GError:
            return

    def close_window(_widget, _callback=None):
        window.close()

    def apply_preferences(_widget, _callback=None):
        nonlocal pixbuf
        nonlocal cover_deleted
        nonlocal game_id

        values = {}

        final_name = name.get_buffer().get_text()
        final_developer = developer.get_buffer().get_text()
        final_executable = executable.get_buffer().get_text()

        try:
            # Attempt to parse using shell parsing rules (doesn't verify executable existence).
            final_executable_split = shlex.split(
                final_executable, comments=False, posix=True
            )
        except ValueError as exception:
            create_dialog(
                window,
                _("Couldn't Add Game")
                if not game_id
                else _("Couldn't Apply Preferences"),
                f'{_("Executable")}: {exception}.',
            )
            return

        if not game_id:
            if final_name == "":
                create_dialog(
                    window, _("Couldn't Add Game"), _("Game title cannot be empty.")
                )
                return

            if final_executable == "":
                create_dialog(
                    window, _("Couldn't Add Game"), _("Executable cannot be empty.")
                )
                return

            # Increment the number after the game id (eg. imported_1, imported_2)

            numbers = [0]

            for game in games:
                if "imported_" in game:
                    numbers.append(int(game.replace("imported_", "")))

            game_id = f"imported_{str(max(numbers) + 1)}"

            values["game_id"] = game_id
            values["hidden"] = False
            values["source"] = "imported"
            values["added"] = int(time.time())
            values["last_played"] = 0

        else:
            if final_name == "":
                create_dialog(
                    window,
                    _("Couldn't Apply Preferences"),
                    _("Game title cannot be empty."),
                )
                return

            if final_executable == "":
                create_dialog(
                    window,
                    _("Couldn't Apply Preferences"),
                    _("Executable cannot be empty."),
                )
                return

        values["name"] = final_name
        values["developer"] = final_developer or None
        values["executable"] = final_executable_split

        if cover_deleted:
            (
                parent_widget.data_dir / "cartridges" / "covers" / f"{game_id}.tiff"
            ).unlink(missing_ok=True)
            if game_id in parent_widget.pixbufs:
                parent_widget.pixbufs.pop(game_id)

        if pixbuf:
            save_cover(parent_widget, game_id, None, pixbuf)
        elif not (
            parent_widget.data_dir / "cartridges" / "covers" / f"{game_id}.tiff"
        ).is_file():
            SGDBSave(parent_widget, {(game_id, values["name"])})

        path = parent_widget.data_dir / "cartridges" / "games" / f"{game_id}.json"

        if path.exists():
            data = json.loads(path.read_text("utf-8"))
            data.update(values)
            save_game(parent_widget, data)
        else:
            save_game(parent_widget, values)

        parent_widget.update_games([game_id])
        window.close()
        parent_widget.show_overview(None, game_id)

    def focus_executable(_widget):
        window.set_focus(executable)

    cover_button_edit.connect("clicked", choose_cover)
    cancel_button.connect("clicked", close_window)
    apply_button.connect("clicked", apply_preferences)
    name.connect("activate", focus_executable)
    executable.connect("activate", apply_preferences)

    shortcut_controller = Gtk.ShortcutController()
    shortcut_controller.add_shortcut(
        Gtk.Shortcut.new(
            Gtk.ShortcutTrigger.parse_string("Escape"),
            Gtk.CallbackAction.new(close_window),
        )
    )

    window.add_controller(shortcut_controller)
    window.set_focus(name)
    window.present()
