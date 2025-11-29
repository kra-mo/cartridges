# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo

import locale
from collections.abc import Generator
from typing import Any

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import games
from cartridges.config import PREFIX, PROFILE
from cartridges.games import Game

SORT_MODES = {
    "last_played": ("last-played", True),
    "a-z": ("name", False),
    "z-a": ("name", True),
    "newest": ("added", False),
    "oldest": ("added", True),
}


@Gtk.Template.from_resource(f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    sorter: Gtk.CustomSorter = Gtk.Template.Child()

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    _sort_prop = "last-played"
    _invert_sort = True

    @GObject.Property(type=Gio.ListStore)
    def games(self) -> Gio.ListStore:
        """Model of the user's games."""
        return games.model

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        if PROFILE == "development":
            self.add_css_class("devel")

        # https://gitlab.gnome.org/GNOME/gtk/-/issues/7901
        self.search_entry.set_key_capture_widget(self)
        self.sorter.set_sort_func(self._sort_func)

        self.add_action(Gio.PropertyAction.new("show-hidden", self, "show-hidden"))
        self.add_action_entries((
            ("search", lambda *_: self.search_entry.grab_focus()),
            ("sort", self._sort, "s", "'last_played'"),
        ))

    @Gtk.Template.Callback()
    def _search_started(self, entry: Gtk.SearchEntry) -> None:
        entry.grab_focus()

    @Gtk.Template.Callback()
    def _search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.search_text = entry.props.text
        entry.grab_focus()

    @Gtk.Template.Callback()
    def _stop_search(self, entry: Gtk.SearchEntry) -> None:
        entry.props.text = ""
        self.grid.grab_focus()

    def _sort(self, action: Gio.SimpleAction, parameter: GLib.Variant, *_args) -> None:
        action.change_state(parameter)
        prop, invert = SORT_MODES[parameter.get_string()]
        opposite = (self._sort_prop == prop) and (self._invert_sort != invert)
        self._sort_prop, self._invert_sort = prop, invert
        self.sorter.changed(
            Gtk.SorterChange.INVERTED if opposite else Gtk.SorterChange.DIFFERENT
        )

    def _sort_func(self, game1: Game, game2: Game, _) -> int:
        a = (game2 if self._invert_sort else game1).get_property(self._sort_prop)
        b = (game1 if self._invert_sort else game2).get_property(self._sort_prop)
        return (
            locale.strcoll(*self._sortable(a, b))
            if isinstance(a, str)
            else (a > b) - (a < b)
            or locale.strcoll(*self._sortable(game1.name, game2.name))
        )

    @staticmethod
    def _sortable(*strings: str) -> Generator[str]:
        for string in strings:
            yield string.lower().removeprefix("the ")
