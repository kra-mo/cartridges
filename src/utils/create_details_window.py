# create_details_window.py
#
# Copyright 2022 kramo
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

def create_details_window(parent_widget, game_id = None):
    import os, json, time
    from gi.repository import Adw, Gtk, Gio, GLib, GdkPixbuf
    from .create_dialog import create_dialog
    from .save_games import save_games
    from .save_cover import save_cover

    window = Adw.Window(
        modal = True,
        default_width = 450,
        default_height = 650,
        transient_for = parent_widget
    )

    games = parent_widget.games
    pixbuf = None

    if game_id == None:
        window.set_title(_("Add New Game"))
        cover = Gtk.Picture.new_for_pixbuf(parent_widget.placeholder_pixbuf)
        name = Gtk.Entry()
        executable = Gtk.Entry()
        apply_button = Gtk.Button.new_with_label(_("Confirm"))
    else:
        window.set_title(_("Edit Game Details"))
        cover = Gtk.Picture.new_for_pixbuf((parent_widget.visible_widgets | parent_widget.hidden_widgets)[game_id].pixbuf)
        name = Gtk.Entry.new_with_buffer(Gtk.EntryBuffer.new(games[game_id]["name"], -1))
        executable = Gtk.Entry.new_with_buffer(Gtk.EntryBuffer.new((games[game_id]["executable"]), -1))
        apply_button = Gtk.Button.new_with_label(_("Apply"))

    image_filter = Gtk.FileFilter(
        name= _("Images")
    )
    image_filter.add_pixbuf_formats()
    file_filters = Gio.ListStore.new(Gtk.FileFilter)
    file_filters.append(image_filter)
    filechooser = Gtk.FileDialog()
    filechooser.set_filters(file_filters)

    cover.add_css_class("card")
    cover.set_size_request(200, 300)

    cover_button = Gtk.Button(
        icon_name = "document-edit-symbolic",
        halign = Gtk.Align.END,
        valign = Gtk.Align.END,
        margin_bottom = 6,
        margin_end = 6,
        css_classes = ["circular", "osd"],
    )

    cover_overlay = Gtk.Overlay(
        child = cover,
        halign = Gtk.Align.CENTER,
        valign = Gtk.Align.CENTER,
    )
    cover_overlay.add_overlay(cover_button)

    cover_group = Adw.PreferencesGroup()
    cover_group.add(cover_overlay)

    title_group = Adw.PreferencesGroup(
        title = _("Title"),
        description = _("The title of the game"),
    )
    title_group.add(name)

    exec_group = Adw.PreferencesGroup(
        title = _("Executable"),
        description = _("File to open or command to run when launching the game"),
    )
    exec_group.add(executable)

    general_page = Adw.PreferencesPage()
    general_page.add(cover_group)
    general_page.add(title_group)
    general_page.add(exec_group)

    cancel_button = Gtk.Button.new_with_label(_("Cancel"))

    apply_button.add_css_class("suggested-action")

    header_bar = Adw.HeaderBar(
        show_start_title_buttons = False,
        show_end_title_buttons = False,
    )
    header_bar.pack_start(cancel_button)
    header_bar.pack_end(apply_button)

    main_box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
    main_box.append(header_bar)
    main_box.append(general_page)
    window.set_content(main_box)

    def choose_cover(widget):
        filechooser.open(window, None, set_cover, None)

    def set_cover(source, result, _):
        nonlocal pixbuf
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filechooser.open_finish(result).get_path(), 200, 300, False)
            cover.set_pixbuf(pixbuf)
        except GLib.GError:
            return

    def close_window(widget, callback=None):
        window.close()

    def apply_preferences(widget, callback=None):
        nonlocal pixbuf
        nonlocal game_id

        values = {}

        games_dir = os.path.join(os.environ.get("XDG_DATA_HOME"), "games")
        final_name = name.get_buffer().get_text()
        final_executable = executable.get_buffer().get_text()

        if game_id == None:

            if final_name == "":
                create_dialog(window, _("Couldn't Add Game"), _("Game title cannot be empty."))
                return

            if final_executable == "":
                create_dialog(window, _("Couldn't Add Game"), _("Executable cannot be empty."))
                return

            numbers = [0]

            for game in games:
                if "imported_" in game:
                    numbers.append(int(game.replace("imported_", "")))

            game_id = "imported_" + str(max(numbers)+1)

            games[game_id] = {}

            values["game_id"] = game_id
            values["hidden"] = False
            values["source"] = "imported"
            values["added"] = int(time.time())
            values["last_played"] = 0

        else:
            if final_name == "":
                create_dialog(window, _("Couldn't Apply Preferences"), _("Game title cannot be empty."))
                return

            if final_executable == "":
                create_dialog(window, _("Couldn't Apply Preferences"), _("Executable cannot be empty."))
                return

        if pixbuf != None:
            values["pixbuf_options"] = save_cover(None, parent_widget, None, pixbuf, game_id)

        values["name"] = final_name
        values["executable"] = final_executable

        games[game_id].update(values)
        save_games(games)
        parent_widget.update_games([game_id])
        if parent_widget.stack.get_visible_child() == parent_widget.overview:
            parent_widget.show_overview(None, game_id)
        window.close()
        parent_widget.show_overview(None, game_id)

    def focus_executable(widget):
        window.set_focus(executable)

    cover_button.connect("clicked", choose_cover)
    cancel_button.connect("clicked", close_window)
    apply_button.connect("clicked", apply_preferences)
    name.connect("activate", focus_executable)
    executable.connect("activate", apply_preferences)

    shortcut_controller = Gtk.ShortcutController()
    shortcut_controller.add_shortcut(Gtk.Shortcut.new(Gtk.ShortcutTrigger.parse_string('Escape'), Gtk.CallbackAction.new(close_window)))

    window.add_controller(shortcut_controller)
    window.set_focus(name)
    window.present()

