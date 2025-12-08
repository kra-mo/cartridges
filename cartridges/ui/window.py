# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Callable
from gettext import gettext as _
from typing import Any, TypeVar, cast

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import games, state_settings
from cartridges.config import PREFIX, PROFILE
from cartridges.games import Game, GameSorter

from .game_details import GameDetails
from .game_item import GameItem  # noqa: F401

SORT_MODES = {
    "last_played": ("last-played", True),
    "a-z": ("name", False),
    "z-a": ("name", True),
    "newest": ("added", False),
    "oldest": ("added", True),
}

_T = TypeVar("_T")
type _UndoFunc = Callable[[], Any]


@Gtk.Template.from_resource(f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    sorter: GameSorter = Gtk.Template.Child()
    details: GameDetails = Gtk.Template.Child()

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    @GObject.Property(type=Gio.ListStore)
    def games(self) -> Gio.ListStore:
        """Model of the user's games."""
        return games.model

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        if PROFILE == "development":
            self.add_css_class("devel")

        flags = Gio.SettingsBindFlags.DEFAULT
        state_settings.bind("width", self, "default-width", flags)
        state_settings.bind("height", self, "default-height", flags)
        state_settings.bind("is-maximized", self, "maximized", flags)

        # https://gitlab.gnome.org/GNOME/gtk/-/issues/7901
        self.search_entry.set_key_capture_widget(self)

        self.add_action(state_settings.create_action("sort-mode"))
        self.add_action(Gio.PropertyAction.new("show-hidden", self, "show-hidden"))
        self.add_action_entries((
            ("search", lambda *_: self.search_entry.grab_focus()),
            ("edit", lambda _action, param, *_: self._edit(param.get_uint32()), "u"),
            ("add", lambda *_: self._add()),
            ("undo", lambda *_: self._undo()),
        ))

        self._history: dict[Adw.Toast, _UndoFunc] = {}

    def send_toast(self, title: str, *, undo: _UndoFunc | None = None):
        """Notify the user with a toast.

        Optionally display a button allowing the user to `undo` an operation.
        """
        toast = Adw.Toast.new(title)
        if undo:
            toast.props.button_label = _("Undo")
            toast.props.priority = Adw.ToastPriority.HIGH
            toast.connect("button-clicked", lambda toast: self._undo(toast))
            self._history[toast] = undo

        self.toast_overlay.add_toast(toast)

    @Gtk.Template.Callback()
    def _if_else(self, _obj, condition: object, first: _T, second: _T) -> _T:
        return first if condition else second

    @Gtk.Template.Callback()
    def _show_details(self, grid: Gtk.GridView, position: int):
        self.details.game = cast(Gio.ListModel, grid.props.model).get_item(position)
        self.navigation_view.push_by_tag("details")

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

    @Gtk.Template.Callback()
    def _sort_changed(self, *_args):
        self.sorter.changed(Gtk.SorterChange.DIFFERENT)

    def _edit(self, pos: int):
        self.details.game = cast(Gio.ListModel, self.grid.props.model).get_item(pos)
        self.navigation_view.push_by_tag("details")
        self.details.edit()

    def _add(self):
        self.details.game = Game.for_editing()

        if self.navigation_view.props.visible_page_tag != "details":
            self.navigation_view.push_by_tag("details")

        self.details.edit()

    def _undo(self, toast: Adw.Toast | None = None):
        if toast:
            self._history.pop(toast)()
            return

        try:
            toast, undo = self._history.popitem()
        except KeyError:
            return

        toast.dismiss()
        undo()
