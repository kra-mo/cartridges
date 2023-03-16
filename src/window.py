# window.py
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

import datetime
import os

from gi.repository import Adw, GdkPixbuf, Gio, GLib, Gtk

from .game import game
from .get_cover import get_cover
from .get_games import get_games
from .save_games import save_games


@Gtk.Template(resource_path="/hu/kramo/Cartridges/gtk/window.ui")
class CartridgesWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CartridgesWindow"

    toast_overlay = Gtk.Template.Child()
    primary_menu_button = Gtk.Template.Child()
    stack = Gtk.Template.Child()
    overview = Gtk.Template.Child()
    library_view = Gtk.Template.Child()
    library = Gtk.Template.Child()
    scrolledwindow = Gtk.Template.Child()
    library_bin = Gtk.Template.Child()
    notice_empty = Gtk.Template.Child()
    notice_no_results = Gtk.Template.Child()
    game_options = Gtk.Template.Child()
    search_bar = Gtk.Template.Child()
    search_entry = Gtk.Template.Child()
    search_button = Gtk.Template.Child()

    overview_box = Gtk.Template.Child()
    overview_cover = Gtk.Template.Child()
    overview_title = Gtk.Template.Child()
    overview_header_bar_title = Gtk.Template.Child()
    overview_launch = Gtk.Template.Child()
    overview_blurred_cover = Gtk.Template.Child()
    overview_menu_button = Gtk.Template.Child()
    overview_developer = Gtk.Template.Child()
    overview_added = Gtk.Template.Child()
    overview_last_played = Gtk.Template.Child()

    hidden_library = Gtk.Template.Child()
    hidden_library_view = Gtk.Template.Child()
    hidden_scrolledwindow = Gtk.Template.Child()
    hidden_library_bin = Gtk.Template.Child()
    hidden_notice_empty = Gtk.Template.Child()
    hidden_game_options = Gtk.Template.Child()
    hidden_search_bar = Gtk.Template.Child()
    hidden_search_entry = Gtk.Template.Child()
    hidden_search_button = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.games = {}
        self.visible_widgets = {}
        self.hidden_widgets = {}
        self.filtered = {}
        self.hidden_filtered = {}
        self.previous_page = self.library_view
        self.toasts = {}
        self.pixbufs = {}
        self.active_game_id = None

        self.overview.set_measure_overlay(self.overview_box, True)
        self.overview.set_clip_overlay(self.overview_box, False)

        self.schema = Gio.Settings.new("hu.kramo.Cartridges")
        self.placeholder_pixbuf = GdkPixbuf.Pixbuf.new_from_resource_at_scale(
            "/hu/kramo/Cartridges/library_placeholder.svg", 200, 300, False
        )
        current_games = get_games()
        for current_game in current_games:
            if "removed" in current_games[current_game].keys():
                os.remove(
                    os.path.join(
                        os.getenv("XDG_DATA_HOME")
                        or os.path.expanduser(os.path.join("~", ".local", "share")),
                        "cartridges",
                        "games",
                        current_game + ".json",
                    )
                )
                try:
                    os.remove(
                        os.path.join(
                            os.getenv("XDG_DATA_HOME")
                            or os.path.expanduser(os.path.join("~", ".local", "share")),
                            "cartridges",
                            "covers",
                            current_game + ".dat",
                        )
                    )
                except FileNotFoundError:
                    pass

        self.library.set_filter_func(self.search_filter)
        self.hidden_library.set_filter_func(self.hidden_search_filter)

        self.update_games(get_games())

        # Connect signals
        self.search_entry.connect("search-changed", self.search_changed, False)
        self.hidden_search_entry.connect("search-changed", self.search_changed, True)

        back_mouse_button = Gtk.GestureClick(button=8)
        back_mouse_button.connect("pressed", self.on_go_back_action)
        self.add_controller(back_mouse_button)

    def update_games(self, games):
        current_games = get_games()

        for game_id in games:
            if game_id in self.visible_widgets:
                self.library.remove(self.visible_widgets[game_id])
                self.filtered.pop(self.visible_widgets[game_id])
                self.visible_widgets.pop(game_id)
            elif game_id in self.hidden_widgets:
                self.hidden_library.remove(self.hidden_widgets[game_id])
                self.hidden_filtered.pop(self.hidden_widgets[game_id])
                self.hidden_widgets.pop(game_id)

            current_game = current_games[game_id]

            entry = game(self, current_game)
            self.games[current_game["game_id"]] = entry

            if entry.removed:
                continue
            if entry.blacklisted:
                continue

            if not self.games[game_id].hidden:
                self.visible_widgets[game_id] = entry
                self.library.append(entry)
            else:
                self.hidden_widgets[game_id] = entry
                entry.menu_button.set_menu_model(entry.hidden_game_options)
                self.hidden_library.append(entry)

            entry.cover_button.connect("clicked", self.show_overview, game_id)
            entry.menu_button.get_popover().connect(
                "notify::visible", self.set_active_game, game_id
            )
            entry.get_parent().set_focusable(False)

        if not self.visible_widgets:
            self.library_bin.set_child(self.notice_empty)
        else:
            self.library_bin.set_child(self.scrolledwindow)

        if not self.hidden_widgets:
            self.hidden_library_bin.set_child(self.hidden_notice_empty)
        else:
            self.hidden_library_bin.set_child(self.hidden_scrolledwindow)

        self.library.invalidate_filter()
        self.hidden_library.invalidate_filter()

    def search_changed(self, _widget, hidden):
        # Refresh search filter on keystroke in search box
        if not hidden:
            self.library.invalidate_filter()
        else:
            self.hidden_library.invalidate_filter()

    def search_filter(self, child):
        # Only show games matching the contents of the search box
        text = self.search_entry.get_text().lower()
        if text == "":
            filtered = True
        elif text in child.get_first_child().name.lower():
            filtered = True
        else:
            filtered = False

        # Add filtered entry to dict of filtered widgets
        self.filtered[child.get_first_child()] = filtered

        if True not in self.filtered.values():
            self.library_bin.set_child(self.notice_no_results)
        else:
            self.library_bin.set_child(self.scrolledwindow)
        return filtered

    def hidden_search_filter(self, child):
        text = self.hidden_search_entry.get_text().lower()
        if text == "":
            filtered = True
        elif text in child.get_first_child().name.lower():
            filtered = True
        else:
            filtered = False

        self.hidden_filtered[child.get_first_child()] = filtered

        if True not in self.hidden_filtered.values():
            self.hidden_library_bin.set_child(self.notice_no_results)
        else:
            self.hidden_library_bin.set_child(self.hidden_scrolledwindow)
        return filtered

    def set_active_game(self, _widget, _unused, game_id):
        self.active_game_id = game_id

    def get_time(self, timestamp):
        date = datetime.datetime.fromtimestamp(timestamp)

        if (datetime.datetime.today() - date).days == 0:
            return _("Today")
        if (datetime.datetime.today() - date).days == 1:
            return _("Yesterday")
        if (datetime.datetime.today() - date).days < 8:
            return GLib.DateTime.new_from_unix_utc(timestamp).format("%A")
        return GLib.DateTime.new_from_unix_utc(timestamp).format("%x")

    def show_overview(self, _widget, game_id):
        current_game = self.games[game_id]

        if current_game.developer:
            self.overview_developer.set_label(current_game.developer)
            self.overview_developer.set_visible(True)
        else:
            self.overview_developer.set_visible(False)

        if not current_game.hidden:
            self.overview_menu_button.set_menu_model(self.game_options)
        else:
            self.overview_menu_button.set_menu_model(self.hidden_game_options)

        if self.stack.get_visible_child() != self.overview:
            self.stack.set_transition_type(Gtk.StackTransitionType.OVER_LEFT)
            self.stack.set_visible_child(self.overview)

        self.active_game_id = game_id
        pixbuf = get_cover(self.active_game_id, self)
        self.overview_cover.set_pixbuf(pixbuf)
        self.overview_blurred_cover.set_pixbuf(
            pixbuf.scale_simple(2, 3, GdkPixbuf.InterpType.BILINEAR)
        )
        self.overview_title.set_label(current_game.name)
        self.overview_header_bar_title.set_title(current_game.name)
        self.overview_added.set_label(
            _("Added:") + " " + self.get_time(current_game.added)
        )
        self.overview_last_played.set_label(
            _("Last played:") + " " + self.get_time(current_game.last_played)
            if current_game.last_played != 0
            else _("Last played: Never")
        )

    def a_z_sort(self, child1, child2):
        name1 = child1.get_first_child().name.lower()
        name2 = child2.get_first_child().name.lower()
        if name1 > name2:
            return 1
        if name1 < name2:
            return -1
        if child1.get_first_child().game_id > child2.get_first_child().game_id:
            return 1
        return -1

    def z_a_sort(self, child1, child2):
        name1 = child1.get_first_child().name.lower()
        name2 = child2.get_first_child().name.lower()
        if name1 > name2:
            return -1
        if name1 < name2:
            return 1
        return self.a_z_sort(child1, child2)

    def newest_sort(self, child1, child2):
        time1 = self.games[child1.get_first_child().game_id].added
        time2 = self.games[child2.get_first_child().game_id].added
        if time1 > time2:
            return -1
        if time1 < time2:
            return 1
        return self.a_z_sort(child1, child2)

    def oldest_sort(self, child1, child2):
        time1 = self.games[child1.get_first_child().game_id].added
        time2 = self.games[child2.get_first_child().game_id].added
        if time1 > time2:
            return 1
        if time1 < time2:
            return -1
        return self.a_z_sort(child1, child2)

    def last_played_sort(self, child1, child2):
        time1 = self.games[child1.get_first_child().game_id].last_played
        time2 = self.games[child2.get_first_child().game_id].last_played
        if time1 > time2:
            return -1
        if time1 < time2:
            return 1
        return self.a_z_sort(child1, child2)

    def on_go_back_action(self, _widget, _unused, _x=None, _y=None):
        if self.stack.get_visible_child() == self.hidden_library_view:
            self.on_show_library_action(None, None)
        elif self.stack.get_visible_child() == self.overview:
            self.on_go_to_parent_action(None, None)

    def on_go_to_parent_action(self, _widget, _unused):
        if self.stack.get_visible_child() == self.overview:
            if self.previous_page == self.library_view:
                self.on_show_library_action(None, None)
            else:
                self.on_show_hidden_action(None, None)

    def on_show_library_action(self, _widget, _unused):
        self.stack.set_transition_type(Gtk.StackTransitionType.UNDER_RIGHT)
        self.stack.set_visible_child(self.library_view)
        self.lookup_action("show_hidden").set_enabled(True)
        self.previous_page = self.library_view

    def on_show_hidden_action(self, _widget, _unused):
        if self.stack.get_visible_child() == self.library_view:
            self.stack.set_transition_type(Gtk.StackTransitionType.OVER_LEFT)
        else:
            self.stack.set_transition_type(Gtk.StackTransitionType.UNDER_RIGHT)
        self.lookup_action("show_hidden").set_enabled(False)
        self.stack.set_visible_child(self.hidden_library_view)
        self.previous_page = self.hidden_library_view

    def on_sort_action(self, action, state):
        action.set_state(state)
        state = str(state).strip("'")

        if state == "a-z":
            sort_func = self.a_z_sort

        elif state == "z-a":
            sort_func = self.z_a_sort

        elif state == "newest":
            sort_func = self.newest_sort

        elif state == "oldest":
            sort_func = self.oldest_sort

        else:
            sort_func = self.last_played_sort

        Gio.Settings(schema_id="hu.kramo.Cartridge.State").set_string(
            "sort-mode", state
        )
        self.library.set_sort_func(sort_func)
        self.hidden_library.set_sort_func(sort_func)

    def on_toggle_search_action(self, _widget, _unused):
        if self.stack.get_visible_child() == self.library_view:
            search_bar = self.search_bar
            search_entry = self.search_entry
            search_button = self.search_button
        elif self.stack.get_visible_child() == self.hidden_library_view:
            search_bar = self.hidden_search_bar
            search_entry = self.hidden_search_entry
            search_button = self.hidden_search_button
        else:
            return

        search_mode = search_bar.get_search_mode()
        search_bar.set_search_mode(not search_mode)
        search_button.set_active(not search_button.get_active())

        if not search_mode:
            self.set_focus(search_entry)
        else:
            search_entry.set_text("")

    def on_escape_action(self, _widget, _unused):
        if self.stack.get_visible_child() == self.overview:
            self.on_go_back_action(None, None)
            return
        if self.stack.get_visible_child() == self.library_view:
            search_bar = self.search_bar
            search_entry = self.search_entry
            search_button = self.search_button
        elif self.stack.get_visible_child() == self.hidden_library_view:
            search_bar = self.hidden_search_bar
            search_entry = self.hidden_search_entry
            search_button = self.hidden_search_button
        else:
            return

        if self.get_focus() == search_entry.get_focus_child():
            search_bar.set_search_mode(False)
            search_button.set_active(False)
            search_entry.set_text("")

    def on_undo_remove_action(self, _widget, game_id=None):
        # Remove the "removed=True" property from the game and dismiss the toast

        if not game_id:
            try:
                game_id = list(self.toasts)[-1]
            except IndexError:
                return
        data = get_games([game_id])[game_id]
        data.pop("removed")
        save_games({game_id: data})
        self.update_games([game_id])
        self.toasts[game_id].dismiss()
        self.toasts.pop(game_id)

    def on_open_menu_action(self, _widget, _unused):
        if self.stack.get_visible_child() != self.overview:
            self.primary_menu_button.set_active(True)
        else:
            self.overview_menu_button.set_active(True)
