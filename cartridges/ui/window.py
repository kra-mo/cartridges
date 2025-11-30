# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo

import locale
from collections.abc import Generator
from datetime import UTC, datetime
from gettext import gettext as _
from typing import Any

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk

from cartridges import games, state_settings
from cartridges.config import PREFIX, PROFILE
from cartridges.games import Game

from .cover import Cover  # noqa: F401

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

    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    sorter: Gtk.CustomSorter = Gtk.Template.Child()

    active_game = GObject.Property(type=Game)
    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    _sort_prop = "last-played"
    _invert_sort = True

    @GObject.Property(type=Gio.ListStore)
    def games(self) -> Gio.ListStore:
        """Model of the user's games."""
        return games.model

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
            ("sort", self._sort, "s", "'last_played'"),
        ))

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
