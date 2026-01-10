# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import sys
from collections.abc import Callable
from gettext import gettext as _
from typing import Any, cast

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import STATE_SETTINGS
from cartridges.collections import Collection
from cartridges.config import PREFIX, PROFILE
from cartridges.sources import imported
from cartridges.ui import closures, collections, games, sources

from .collection_details import CollectionDetails
from .collections import CollectionFilter, CollectionSidebarItem
from .game_details import GameDetails
from .game_item import GameItem  # noqa: F401
from .games import GameSorter
from .sources import SourceSidebarItem

if sys.platform.startswith("linux"):
    from cartridges import gamepads
    from cartridges.gamepads import Gamepad

GObject.type_ensure(GObject.SignalGroup)

type _UndoFunc = Callable[[], Any]


@Gtk.Template.from_resource(f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    split_view: Adw.OverlaySplitView = Gtk.Template.Child()
    sidebar: Adw.Sidebar = Gtk.Template.Child()  # pyright: ignore[reportAttributeAccessIssue]
    sources: Adw.SidebarSection = Gtk.Template.Child()  # pyright: ignore[reportAttributeAccessIssue]
    collections: Adw.SidebarSection = Gtk.Template.Child()  # pyright: ignore[reportAttributeAccessIssue]
    new_collection_item: Adw.SidebarItem = Gtk.Template.Child()  # pyright: ignore[reportAttributeAccessIssue]
    collection_menu: Gio.Menu = Gtk.Template.Child()
    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    title_box: Gtk.CenterBox = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    sort_button: Gtk.MenuButton = Gtk.Template.Child()
    main_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    sorter: GameSorter = Gtk.Template.Child()
    collection_filter: CollectionFilter = Gtk.Template.Child()
    details: GameDetails = Gtk.Template.Child()

    collection = GObject.Property(type=Collection)
    collection_signals: GObject.SignalGroup = Gtk.Template.Child()
    model = GObject.Property(type=Gio.ListModel)
    model_signals: GObject.SignalGroup = Gtk.Template.Child()

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    settings = GObject.Property(type=Gtk.Settings)

    _selected_sidebar_item = 0

    format_string = closures.format_string
    if_else = closures.if_else

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
        self.sources.bind_model(
            sources.model,
            lambda source: SourceSidebarItem(source),
        )
        self.collections.bind_model(
            collections.model,
            lambda collection: CollectionSidebarItem(collection),
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
            (
                "add-collection",
                lambda _action, param, *_: self._add_collection(param.get_string()),
                "s",
            ),
            (
                "edit-collection",
                lambda _action, param, *_: self._edit_collection(param.get_uint32()),
                "u",
            ),
            (
                "remove-collection",
                lambda _action, param, *_: self._remove_collection(param.get_uint32()),
                "u",
            ),
            (
                "notify-collection-filter",
                lambda *_: self.collection_filter.changed(Gtk.FilterChange.DIFFERENT),
            ),
            ("undo", lambda *_: self._undo()),
        ))

        self.collection_signals.connect_closure(
            "notify::removed",
            lambda *_: self._collection_removed(),
            after=True,
        )
        self.model_signals.connect_closure(
            "items-changed",
            lambda model, *_: None if model else self._model_emptied(),
            after=True,
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
            toast.connect("button-clicked", lambda toast: self._undo(toast))
            self._history[toast] = undo

        self.toast_overlay.add_toast(toast)

    def _collection_removed(self):
        self.collection = None
        self.sidebar.props.selected = 0

    def _model_emptied(self):
        self.model = games.model
        self.sidebar.props.selected = 0

    @Gtk.Template.Callback()
    def _show_sidebar_title(self, _obj, layout: str) -> bool:
        right_window_controls = layout.replace("appmenu", "").startswith(":")
        return right_window_controls and not sys.platform.startswith("darwin")

    @Gtk.Template.Callback()
    def _navigate(self, sidebar: Adw.Sidebar, index: int):  # pyright: ignore[reportAttributeAccessIssue]
        item = sidebar.get_item(index)

        match item:
            case self.new_collection_item:
                self._add_collection()
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

    @Gtk.Template.Callback()
    def _update_selection(self, sidebar: Adw.Sidebar, *_args):  # pyright: ignore[reportAttributeAccessIssue]
        if sidebar.props.selected_item is self.new_collection_item:
            sidebar.props.selected = self._selected_sidebar_item
        self._selected_sidebar_item = sidebar.props.selected

    @Gtk.Template.Callback()
    def _setup_sidebar_menu(self, _sidebar, item: Adw.SidebarItem):  # pyright: ignore[reportAttributeAccessIssue]
        if isinstance(item, CollectionSidebarItem):
            menu = self.collection_menu
            menu.remove_all()
            menu.append(
                _("Edit"),
                f"win.edit-collection(uint32 {item.get_section_index()})",
            )
            menu.append(
                _("Remove"),
                f"win.remove-collection(uint32 {item.get_section_index()})",
            )

    @Gtk.Template.Callback()
    def _setup_gamepad_monitor(self, *_args):
        if sys.platform.startswith("linux"):
            Gamepad.window = self  # pyright: ignore[reportPossiblyUnboundVariable]
            gamepads.setup_monitor()  # pyright: ignore[reportPossiblyUnboundVariable]

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
        self.details.game = imported.new()

        if self.navigation_view.props.visible_page_tag != "details":
            self.navigation_view.push_by_tag("details")

        self.details.edit()

    def _add_collection(self, game_id: str | None = None):
        collection = Collection()
        if game_id:
            collection.game_ids.add(game_id)

        details = CollectionDetails(collection)
        details.present(self)

    def _edit_collection(self, pos: int):
        collection = self.collections.get_item(pos).collection
        details = CollectionDetails(collection)
        details.connect(
            "sort-changed",
            lambda *_: collections.sorter.changed(Gtk.SorterChange.DIFFERENT),
        )
        details.present(self)

    def _remove_collection(self, pos: int):
        collection = self.collections.get_item(pos).collection
        collection.activate_action("remove")

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
