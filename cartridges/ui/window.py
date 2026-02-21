# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2026 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import sys
from collections.abc import Callable
from gettext import gettext as _
from typing import Any, cast

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import STATE_SETTINGS
from cartridges.collections import Collection
from cartridges.config import PROFILE

from . import collections, games, sources
from .collections import CollectionActions, CollectionSidebarItem
from .game_details import GameDetails
from .game_item import GameItem  # noqa: F401
from .games import GameActions
from .sources import SourceSidebarItem
from .template import Child, template

if sys.platform.startswith("linux"):
    from cartridges import gamepads
    from cartridges.gamepads import Gamepad

GObject.type_ensure(GObject.SignalGroup)

type _UndoFunc = Callable[[], Any]


@template
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    split_view: Child[Adw.OverlaySplitView]
    sidebar: Child[Adw.Sidebar]
    sources: Child[Adw.SidebarSection]
    collections: Child[Adw.SidebarSection]
    new_collection_item: Child[Adw.SidebarItem]
    navigation_view: Child[Adw.NavigationView]
    header_bar: Child[Adw.HeaderBar]
    title_box: Child[Gtk.CenterBox]
    search_entry: Child[Gtk.SearchEntry]
    sort_button: Child[Gtk.MenuButton]
    main_menu_button: Child[Gtk.MenuButton]
    toast_overlay: Child[Adw.ToastOverlay]
    view_stack: Child[Adw.ViewStack]
    grid: Child[Gtk.GridView]
    details: Child[GameDetails]

    game_actions: Child[GameActions]
    menu_collection_actions: Child[CollectionActions]
    collection_signals: Child[GObject.SignalGroup]
    model_signals: Child[GObject.SignalGroup]

    menu_collection = GObject.Property(type=Collection)
    collection = GObject.Property(type=Collection)
    model = GObject.Property(type=Gio.ListModel)

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    settings = GObject.Property(type=Gtk.Settings)

    _selected_sidebar_item = 0

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

        self.sources.bind_model(sources.model, SourceSidebarItem)
        self.collections.bind_model(collections.model, CollectionSidebarItem)

        self.add_action(STATE_SETTINGS.create_action("show-sidebar"))
        self.add_action(STATE_SETTINGS.create_action("sort-mode"))
        self.add_action(
            Gio.PropertyAction(
                name="show-hidden",
                object=self,
                property_name="show-hidden",
            )
        )
        self.add_action_entries((
            ("search", lambda *_: self.search_entry.grab_focus()),
            ("undo", lambda *_: self._undo()),
        ))

        self.insert_action_group("game", self.game_actions)
        self.insert_action_group("collection", self.menu_collection_actions)
        self.collection_signals.connect_closure(
            "notify::removed",
            lambda *_: self._collection_removed(),
            after=False,
        )
        self.model_signals.connect_closure(
            "items-changed",
            lambda model, *_: None if model else self._model_emptied(),
            after=False,
        )
        self.model = games.model

        self._history: dict[Adw.Toast, _UndoFunc] = {}

    def send_toast(self, title: str, *, undo: _UndoFunc | None = None):
        """Notify the user with a toast.

        Optionally display a button allowing the user to `undo` an operation.
        """
        toast = Adw.Toast(title=title, use_markup=False)
        if undo:
            toast.props.button_label = _("Undo")
            toast.props.priority = Adw.ToastPriority.HIGH
            toast.connect("button-clicked", self._undo)
            self._history[toast] = undo

        self.toast_overlay.add_toast(toast)

    def _collection_removed(self):
        self.collection = None
        self.sidebar.props.selected = 0

    def _model_emptied(self):
        self.model = games.model
        self.sidebar.props.selected = 0

    def _show_sidebar_title(self, _obj, layout: str) -> bool:
        right_window_controls = layout.replace("appmenu", "").startswith(":")
        return right_window_controls and not sys.platform.startswith("darwin")

    def _navigate(self, sidebar: Adw.Sidebar, index: int):
        item = sidebar.get_item(index)

        match item:
            case self.new_collection_item:
                collections.add()
                sidebar.props.selected = self._selected_sidebar_item
            case SourceSidebarItem():
                self.collection = None
                self.model = item.model
            case CollectionSidebarItem():
                self.collection = item.collection
                self.model = games.model
            case _:
                self.collection = None
                self.model = games.model

        if item is not self.new_collection_item:
            self._selected_sidebar_item = index

        if self.split_view.props.collapsed:
            self.split_view.props.show_sidebar = False

    def _update_selection(self, sidebar: Adw.Sidebar, *_args):
        if sidebar.props.selected_item is self.new_collection_item:
            sidebar.props.selected = self._selected_sidebar_item
        self._selected_sidebar_item = sidebar.props.selected

    def _setup_sidebar_menu(self, _sidebar, item: Adw.SidebarItem):
        if isinstance(item, CollectionSidebarItem):
            self.menu_collection = item.collection

    def _setup_gamepad_monitor(self, *_args):
        if sys.platform.startswith("linux"):
            Gamepad.window = self  # pyright: ignore[reportPossiblyUnboundVariable]
            gamepads.setup_monitor()  # pyright: ignore[reportPossiblyUnboundVariable]

    def _show_details(self, grid: Gtk.GridView, position: int):
        self.details.game = cast(Gio.ListModel, grid.props.model).get_item(position)
        self.navigation_view.push_by_tag("details")

    def _search_started(self, entry: Gtk.SearchEntry):
        entry.grab_focus()

    def _search_changed(self, entry: Gtk.SearchEntry):
        self.search_text = entry.props.text
        entry.grab_focus()

    def _search_activate(self, _entry):
        self.grid.activate_action("list.activate-item", GLib.Variant("u", 0))

    def _stop_search(self, entry: Gtk.SearchEntry):
        entry.props.text = ""
        self.grid.grab_focus()

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
