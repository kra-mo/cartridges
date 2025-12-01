# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import locale
from collections.abc import Generator
from datetime import UTC, datetime
from gettext import gettext as _
from typing import Any, TypeVar

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from cartridges import games, state_settings
from cartridges.config import PREFIX, PROFILE
from cartridges.games import Game

from .cover import Cover  # noqa: F401
from .game_item import GameItem  # noqa: F401

SORT_MODES = {
    "last_played": ("last-played", True),
    "a-z": ("name", False),
    "z-a": ("name", True),
    "newest": ("added", False),
    "oldest": ("added", True),
}

_T = TypeVar("_T")


@Gtk.Template.from_resource(f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    sorter: Gtk.CustomSorter = Gtk.Template.Child()

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    @GObject.Property(type=Gio.ListStore)
    def games(self) -> Gio.ListStore:
        """Model of the user's games."""
        return games.model

    @GObject.Property(type=Game)
    def active_game(self) -> Game | None:
        """The game whose details to show."""
        return self._active_game

    @active_game.setter
    def active_game(self, active_game: Game | None):
        self._active_game = active_game
        self.insert_action_group("game", active_game)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        if PROFILE == "development":
            self.add_css_class("devel")

        for key, name in {
            "width": "default-width",
            "height": "default-height",
            "is-maximized": "maximized",
        }.items():
            state_settings.bind(key, self, name, Gio.SettingsBindFlags.DEFAULT)

        # https://gitlab.gnome.org/GNOME/gtk/-/issues/7901
        self.search_entry.set_key_capture_widget(self)
        self.sorter.set_sort_func(self._sort_func)

        self.add_action(Gio.PropertyAction.new("show-hidden", self, "show-hidden"))
        self.add_action_entries((
            ("search", lambda *_: self.search_entry.grab_focus()),
            (
                "sort",
                self._sort,
                "s",
                state_settings.get_value("sort-mode").print_(False),
            ),
        ))

    @Gtk.Template.Callback()
    def _if_else(self, _obj, condition: bool, first: _T, second: _T) -> _T:
        return first if condition else second

    @Gtk.Template.Callback()
    def _activate_game(self, grid: Gtk.GridView, position: int):
        if isinstance(model := grid.props.model, Gio.ListModel):
            self.active_game = model.get_item(position)
            self.navigation_view.push_by_tag("details")

    @Gtk.Template.Callback()
    def _downscale_image(self, _obj, cover: Gdk.Texture | None) -> Gdk.Texture | None:
        if cover and (renderer := self.get_renderer()):
            cover.snapshot(snapshot := Gtk.Snapshot.new(), 3, 3)
            if node := snapshot.to_node():
                return renderer.render_texture(node)

        return None

    @Gtk.Template.Callback()
    def _date_label(self, _obj, label: str, timestamp: int) -> str:
        date = datetime.fromtimestamp(timestamp, UTC)
        now = datetime.now(UTC)
        return label.format(
            _("Never")
            if not timestamp
            else _("Today")
            if (n_days := (now - date).days) == 0
            else _("Yesterday")
            if n_days == 1
            else date.strftime("%A")
            if n_days <= (day_of_week := now.weekday())
            else _("Last Week")
            if n_days <= day_of_week + 7
            else _("This Month")
            if n_days <= (day_of_month := now.day)
            else _("Last Month")
            if n_days <= day_of_month + 30
            else date.strftime("%B")
            if n_days < (day_of_year := now.timetuple().tm_yday)
            else _("Last Year")
            if n_days <= day_of_year + 365
            else date.strftime("%Y")
        )

    @Gtk.Template.Callback()
    def _bool(self, _obj, o: object) -> bool:
        return bool(o)

    @Gtk.Template.Callback()
    def _pop(self, _obj):
        self.navigation_view.pop()

    @Gtk.Template.Callback()
    def _search_started(self, entry: Gtk.SearchEntry):
        entry.grab_focus()

    @Gtk.Template.Callback()
    def _search_changed(self, entry: Gtk.SearchEntry):
        self.search_text = entry.props.text
        entry.grab_focus()

    @Gtk.Template.Callback()
    def _search_activate(self, _entry):
        self.grid.activate_action("list.activate-item", GLib.Variant.new_uint32(0))

    @Gtk.Template.Callback()
    def _stop_search(self, entry: Gtk.SearchEntry):
        entry.props.text = ""
        self.grid.grab_focus()

    def _sort(self, action: Gio.SimpleAction, parameter: GLib.Variant, *_args):
        action.change_state(parameter)
        sort_mode = parameter.get_string()

        prop, invert = SORT_MODES[sort_mode]
        prev_prop, prev_invert = SORT_MODES[state_settings.get_string("sort-mode")]
        opposite = (prev_prop == prop) and (prev_invert != invert)

        state_settings.set_string("sort-mode", sort_mode)
        self.sorter.changed(
            Gtk.SorterChange.INVERTED if opposite else Gtk.SorterChange.DIFFERENT
        )

    def _sort_func(self, game1: Game, game2: Game, _) -> int:
        prop, invert = SORT_MODES[state_settings.get_string("sort-mode")]
        a = (game2 if invert else game1).get_property(prop)
        b = (game1 if invert else game2).get_property(prop)
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
