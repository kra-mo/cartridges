# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import sys
from collections.abc import Callable
from gettext import gettext as _
from typing import Any, TypeVar, cast

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import STATE_SETTINGS, collections, games
from cartridges.collections import Collection
from cartridges.config import PREFIX, PROFILE
from cartridges.games import Game

from .collections import (
    CollectionFilter,  # noqa: F401
    CollectionSidebarItem,
)
from .game_details import GameDetails
from .game_item import GameItem  # noqa: F401
from .games import GameSorter

if sys.platform.startswith("linux"):
    from cartridges import gamepads
    from cartridges.gamepads import Gamepad

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

    split_view: Adw.OverlaySplitView = Gtk.Template.Child()
    collections: Adw.SidebarSection = Gtk.Template.Child()  # pyright: ignore[reportAttributeAccessIssue]
    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    title_box: Gtk.CenterBox = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    sort_button: Gtk.MenuButton = Gtk.Template.Child()
    main_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    sorter: GameSorter = Gtk.Template.Child()
    details: GameDetails = Gtk.Template.Child()

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)
    collection = GObject.Property(type=Collection)

    settings = GObject.Property(type=Gtk.Settings)

    @GObject.Property(type=Gio.ListStore)
    def games(self) -> Gio.ListStore:
        """Model of the user's games."""
        return games.model

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        if PROFILE == "development":
            self.add_css_class("devel")

        self.settings = self.get_settings()

        flags = Gio.SettingsBindFlags.DEFAULT
        STATE_SETTINGS.bind("width", self, "default-width", flags)
        STATE_SETTINGS.bind("height", self, "default-height", flags)
        STATE_SETTINGS.bind("is-maximized", self, "maximized", flags)
        STATE_SETTINGS.bind("show-sidebar", self.split_view, "show-sidebar", flags)

        # https://gitlab.gnome.org/GNOME/gtk/-/issues/7901
        self.search_entry.set_key_capture_widget(self)
        self.collections.bind_model(
            collections.model,
            lambda collection: CollectionSidebarItem(collection=collection),
        )

        self.add_action(STATE_SETTINGS.create_action("show-sidebar"))
        self.add_action(STATE_SETTINGS.create_action("sort-mode"))
        self.add_action(Gio.PropertyAction.new("show-hidden", self, "show-hidden"))
        self.add_action_entries((
            ("search", lambda *_: self.search_entry.grab_focus()),
            (
                "edit",
                lambda _action, param, *_: self._edit(param.get_uint32()),
                "u",
            ),
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
    def _show_sidebar_title(self, _obj, layout: str) -> bool:
        right_window_controls = layout.replace("appmenu", "").startswith(":")
        return right_window_controls and not sys.platform.startswith("darwin")

    @Gtk.Template.Callback()
    def _navigate(self, sidebar: Adw.Sidebar, index: int):  # pyright: ignore[reportAttributeAccessIssue]
        item = sidebar.get_item(index)
        self.collection = (
            item.collection if isinstance(item, CollectionSidebarItem) else None
        )

    @Gtk.Template.Callback()
    def _setup_gamepad_monitor(self, *_args):
        if sys.platform.startswith("linux"):
            Gamepad.window = self  # pyright: ignore[reportPossiblyUnboundVariable]
            gamepads.setup_monitor()  # pyright: ignore[reportPossiblyUnboundVariable]

    @Gtk.Template.Callback()
    def _if_else(self, _obj, condition: object, first: _T, second: _T) -> _T:
        return first if condition else second

    @Gtk.Template.Callback()
    def _format(self, _obj, string: str, *args: Any) -> str:
        return string.format(*args)

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
