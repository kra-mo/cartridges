# window.py
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
from datetime import datetime

from gi.repository import Adw, Gio, GLib, Gtk

from . import shared
from .game import Game


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/window.ui")
class CartridgesWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CartridgesWindow"

    toast_overlay = Gtk.Template.Child()
    primary_menu_button = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    details_view = Gtk.Template.Child()
    library_view = Gtk.Template.Child()
    library = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    library_bin = Gtk.Template.Child()
    notice_empty = Gtk.Template.Child()
    notice_no_results = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    search_button = Gtk.Template.Child()

    details_view_box = Gtk.Template.Child()
    details_view_cover = Gtk.Template.Child()
    details_view_spinner = Gtk.Template.Child()
    details_view_title = Gtk.Template.Child()
    details_view_header_bar_title = Gtk.Template.Child()
    details_view_blurred_cover = Gtk.Template.Child()
    details_view_play_button = Gtk.Template.Child()
    details_view_developer = Gtk.Template.Child()
    details_view_added = Gtk.Template.Child()
    details_view_last_played = Gtk.Template.Child()
    details_view_hide_button = Gtk.Template.Child()

    hidden_primary_menu_button = Gtk.Template.Child()
    hidden_library = Gtk.Template.Child()
    hidden_library_view = Gtk.Template.Child()
    hidden_scrolledwindow = Gtk.Template.Child()
    hidden_library_bin = Gtk.Template.Child()
    hidden_notice_empty = Gtk.Template.Child()
    hidden_notice_no_results = Gtk.Template.Child()
    hidden_search_bar = Gtk.Template.Child()
    hidden_search_entry = Gtk.Template.Child()
    hidden_search_button = Gtk.Template.Child()

    games = {}
    game_covers = {}
    toasts = {}
    active_game = None
    details_view_game_cover = None
    sort_state = "a-z"

    # The version of the game_id.json spec
    spec_version = 2.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        shared.win = self

        self.previous_page = self.library_view

        self.details_view.set_measure_overlay(self.details_view_box, True)
        self.details_view.set_clip_overlay(self.details_view_box, False)

        self.library.set_filter_func(self.filter_func)
        self.hidden_library.set_filter_func(self.filter_func)

        self.library.set_sort_func(self.sort_func)
        self.hidden_library.set_sort_func(self.sort_func)

        self.set_library_child()

        games = {}

        if shared.games_dir.exists():
            for open_file in shared.games_dir.iterdir():
                data = json.load(open_file.open())
                games[data["game_id"]] = data

        for game_id, game in games.items():
            if (version := game.get("version")) and version > shared.spec_version:
                continue

            if game.get("removed"):
                for path in (
                    shared.games_dir / f"{game_id}.json",
                    shared.covers_dir / f"{game_id}.tiff",
                    shared.covers_dir / f"{game_id}.gif",
                ):
                    path.unlink(missing_ok=True)
            else:
                Game(game).update()

        # Connect search entries
        self.search_bar.connect_entry(self.search_entry)
        self.hidden_search_bar.connect_entry(self.hidden_search_entry)

        # Connect signals
        self.search_entry.connect("search-changed", self.search_changed, False)
        self.hidden_search_entry.connect("search-changed", self.search_changed, True)

        back_mouse_button = Gtk.GestureClick(button=8)
        (back_mouse_button).connect("pressed", self.on_go_back_action)
        self.add_controller(back_mouse_button)

        style_manager = Adw.StyleManager.get_default()
        style_manager.connect("notify::dark", self.set_details_view_opacity)
        style_manager.connect("notify::high-contrast", self.set_details_view_opacity)

    def search_changed(self, _widget, hidden):
        # Refresh search filter on keystroke in search box
        (self.hidden_library if hidden else self.library).invalidate_filter()

    def set_library_child(self):
        child, hidden_child = self.notice_empty, self.hidden_notice_empty

        for game in self.games.values():
            if game.removed or game.blacklisted:
                continue
            if game.hidden:
                if game.filtered and hidden_child != self.hidden_scrolledwindow:
                    hidden_child = self.hidden_notice_no_results
                    continue
                hidden_child = self.hidden_scrolledwindow
            else:
                if game.filtered and child != self.scrolledwindow:
                    child = self.notice_no_results
                    continue
                child = self.scrolledwindow

        self.library_bin.set_child(child)
        self.hidden_library_bin.set_child(hidden_child)

    def filter_func(self, child):
        game = child.get_child()
        text = (
            (
                self.hidden_search_entry
                if self.stack.get_visible_child() == self.hidden_library_view
                else self.search_entry
            )
            .get_text()
            .lower()
        )

        filtered = text != "" and not (
            text in game.name.lower() or text in game.developer.lower()
            if game.developer
            else None
        )

        game.filtered = filtered
        self.set_library_child()

        return not filtered

    def set_active_game(self, _widget, _pspec, game):
        self.active_game = game

    def get_time(self, timestamp):
        days_no = (datetime.today() - datetime.fromtimestamp(timestamp)).days

        if days_no == 0:
            return _("Today")
        if days_no == 1:
            return _("Yesterday")
        if days_no < 8:
            return GLib.DateTime.new_from_unix_utc(timestamp).format("%A")
        if days_no < 335:
            return GLib.DateTime.new_from_unix_utc(timestamp).format("%B")
        return GLib.DateTime.new_from_unix_utc(timestamp).format("%Y")

    def show_details_view(self, game):
        self.active_game = game

        self.details_view_cover.set_opacity(int(not game.loading))
        self.details_view_spinner.set_spinning(game.loading)

        self.details_view_developer.set_label(game.developer or "")
        self.details_view_developer.set_visible(bool(game.developer))

        icon, text = "view-conceal-symbolic", _("Hide")
        if game.hidden:
            icon, text = "view-reveal-symbolic", _("Unhide")

        self.details_view_hide_button.set_icon_name(icon)
        self.details_view_hide_button.set_tooltip_text(text)

        if self.details_view_game_cover:
            self.details_view_game_cover.pictures.remove(self.details_view_cover)

        self.details_view_game_cover = game.game_cover
        self.details_view_game_cover.add_picture(self.details_view_cover)

        self.details_view_blurred_cover.set_pixbuf(
            self.details_view_game_cover.get_blurred()
        )

        self.details_view_title.set_label(game.name)
        self.details_view_header_bar_title.set_title(game.name)

        date = self.get_time(game.added)
        self.details_view_added.set_label(
            # The variable is the date when the game was added
            _("Added: {}").format(date)
        )
        last_played_date = (
            self.get_time(game.last_played) if game.last_played != 0 else _("Never")
        )
        self.details_view_last_played.set_label(
            # The variable is the date when the game was last played
            _("Last played: {}").format(last_played_date)
        )

        if self.stack.get_visible_child() != self.details_view:
            self.navigate(self.details_view)
            self.set_focus(self.details_view_play_button)

        self.set_details_view_opacity()

    def set_details_view_opacity(self, *_args):
        if self.stack.get_visible_child() != self.details_view:
            return

        if (
            style_manager := Adw.StyleManager.get_default()
        ).get_high_contrast() or not style_manager.get_system_supports_color_schemes():
            self.details_view_blurred_cover.set_opacity(0.3)
            return

        self.details_view_blurred_cover.set_opacity(
            1 - self.details_view_game_cover.luminance[0]
            if style_manager.get_dark()
            else self.details_view_game_cover.luminance[1]
        )

    def sort_func(self, child1, child2):
        var, order = "name", True

        if self.sort_state in ("newest", "oldest"):
            var, order = "added", self.sort_state == "newest"
        elif self.sort_state == "last_played":
            var = "last_played"
        elif self.sort_state == "a-z":
            order = False

        def get_value(index):
            return str(
                getattr((child1.get_child(), child2.get_child())[index], var)
            ).lower()

        if var != "name" and get_value(0) == get_value(1):
            var, order = "name", True

        return ((get_value(0) > get_value(1)) ^ order) * 2 - 1

    def navigate(self, next_page):
        levels = (self.library_view, self.hidden_library_view, self.details_view)
        self.stack.set_transition_type(
            Gtk.StackTransitionType.UNDER_RIGHT
            if levels.index(self.stack.get_visible_child()) - levels.index(next_page)
            > 0
            else Gtk.StackTransitionType.OVER_LEFT
        )

        if next_page in (self.library_view, self.hidden_library_view):
            self.previous_page = next_page
            self.lookup_action("show_hidden").set_enabled(
                next_page == self.library_view
            )

        self.stack.set_visible_child(next_page)

    def on_go_back_action(self, *_args):
        if self.stack.get_visible_child() == self.hidden_library_view:
            self.navigate(self.library_view)
        elif self.stack.get_visible_child() == self.details_view:
            self.on_go_to_parent_action()

    def on_go_to_parent_action(self, *_args):
        if self.stack.get_visible_child() == self.details_view:
            self.navigate(
                self.hidden_library_view
                if self.previous_page == self.hidden_library_view
                else self.library_view
            )

    def on_go_home_action(self, *_args):
        self.navigate(self.library_view)

    def on_show_hidden_action(self, *_args):
        self.navigate(self.hidden_library_view)

    def on_sort_action(self, action, state):
        action.set_state(state)
        self.sort_state = str(state).strip("'")
        self.library.invalidate_sort()

        Gio.Settings(schema_id="hu.kramo.Cartridges.State").set_string(
            "sort-mode", self.sort_state
        )

    def on_toggle_search_action(self, *_args):
        if self.stack.get_visible_child() == self.library_view:
            search_bar = self.search_bar
            search_entry = self.search_entry
        elif self.stack.get_visible_child() == self.hidden_library_view:
            search_bar = self.hidden_search_bar
            search_entry = self.hidden_search_entry
        else:
            return

        search_bar.set_search_mode(not (search_mode := search_bar.get_search_mode()))

        if not search_mode:
            self.set_focus(search_entry)

        search_entry.set_text("")

    def on_escape_action(self, *_args):
        if self.stack.get_visible_child() == self.details_view:
            self.on_go_back_action()
        elif (
            self.get_focus() == self.search_entry.get_focus_child()
            or self.hidden_search_entry.get_focus_child()
        ):
            self.on_toggle_search_action()

    def on_undo_action(self, _widget, game=None, undo=None):
        if not game:  # If the action was activated via Ctrl + Z
            try:
                game = tuple(self.toasts.keys())[-1][0]
                undo = tuple(self.toasts.keys())[-1][1]
            except IndexError:
                return

        if undo == "hide":
            game.toggle_hidden(False)

        elif undo == "remove":
            game.removed = False
            game.save()

        self.toasts[(game, undo)].dismiss()
        self.toasts.pop((game, undo))

    def on_open_menu_action(self, *_args):
        if self.stack.get_visible_child() == self.library_view:
            self.primary_menu_button.popup()
        elif self.stack.get_visible_child() == self.hidden_library_view:
            self.hidden_primary_menu_button.popup()

    def on_close_action(self, *_args):
        self.close()
