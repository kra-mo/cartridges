# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2022-2026 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import math
import sys
from collections.abc import Callable
from gettext import gettext as _
from typing import Any, cast

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import STATE_SETTINGS
from cartridges.collections import Collection
from cartridges.config import PREFIX, PROFILE
from cartridges.gamepads import GamepadNavigable

from . import closures, collections, games, sources
from .collections import CollectionActions, CollectionSidebarItem
from .game_details import GameDetails
from .game_item import GameItem
from .games import GameActions
from .sources import SourceSidebarItem

if sys.platform.startswith("linux"):
    from cartridges import gamepads
    from cartridges.gamepads import Gamepad

GObject.type_ensure(GObject.SignalGroup)

type _UndoFunc = Callable[[], Any]


@Gtk.Template(resource_path=f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow, GamepadNavigable):
    """The main window."""

    __gtype_name__ = __qualname__

    split_view: Adw.OverlaySplitView = Gtk.Template.Child()
    sidebar: Adw.Sidebar = Gtk.Template.Child()
    sources: Adw.SidebarSection = Gtk.Template.Child()
    collections: Adw.SidebarSection = Gtk.Template.Child()
    new_collection_item: Adw.SidebarItem = Gtk.Template.Child()
    navigation_view: Adw.NavigationView = Gtk.Template.Child()
    header_bar: Adw.HeaderBar = Gtk.Template.Child()
    title_box: Gtk.CenterBox = Gtk.Template.Child()
    search_entry: Gtk.SearchEntry = Gtk.Template.Child()
    sort_button: Gtk.MenuButton = Gtk.Template.Child()
    main_menu_button: Gtk.MenuButton = Gtk.Template.Child()
    toast_overlay: Adw.ToastOverlay = Gtk.Template.Child()
    view_stack: Adw.ViewStack = Gtk.Template.Child()
    grid: Gtk.GridView = Gtk.Template.Child()
    details: GameDetails = Gtk.Template.Child()

    game_actions: GameActions = Gtk.Template.Child()
    menu_collection_actions: CollectionActions = Gtk.Template.Child()
    collection_signals: GObject.SignalGroup = Gtk.Template.Child()
    model_signals: GObject.SignalGroup = Gtk.Template.Child()

    menu_collection = GObject.Property(type=Collection)
    collection = GObject.Property(type=Collection)
    model = GObject.Property(type=Gio.ListModel)

    search_text = GObject.Property(type=str)
    show_hidden = GObject.Property(type=bool, default=False)

    settings = GObject.Property(type=Gtk.Settings)

    format_string = closures.format_string
    if_else = closures.if_else
    shortcut = closures.shortcut

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

    def move_focus(self, direction: Gtk.DirectionType):
        """Move focus in main page."""
        # Override GTK's child focus by going up to the search bar,
        # instead of doing nothing when going up on the first row of games.
        if direction == Gtk.DirectionType.UP and (game := self._get_focused_game()):
            current_grid_columns = math.floor(self.grid.get_width() / game.get_width())

            if (self._get_current_game_position() - current_grid_columns) < 0:
                self.search_entry.grab_focus()
                return

        # Override GTK's child focus going to the + button, by going to
        # the grid when leaving sidebar instead
        sidebar_direction = (
            Gtk.DirectionType.LEFT
            if Gtk.Widget.get_default_direction() == Gtk.TextDirection.RTL
            else Gtk.DirectionType.RIGHT
        )
        if direction == sidebar_direction and self.sidebar.get_focus_child():
            self.grid.grab_focus()
            return

        if self.child_focus(direction):
            self.props.focus_visible = True
            return

        self.keynav_failed(direction)

    def activate_button_pressed(self):
        """Activate currently focused widget in the main page."""
        if not (focus_widget := self.props.focus_widget):
            return

        focus_widget.activate()

    def return_button_pressed(self):
        """Return to last used widget in main page."""
        if self.can_close_popover():
            return

        grid_visible = self.view_stack.props.visible_child_name == "grid"
        if self.header_bar.get_focus_child():
            focus_widget = self.grid if grid_visible else self.sidebar

        # If the grid is not visible (i.e.  no search results or imports)
        # the search bar is focused as a fallback.
        focus_widget = (
            self.search_entry
            if not grid_visible
            else (self.grid if self.sidebar.get_focus_child() else self.sidebar)
        )

        focus_widget.grab_focus()
        self.props.focus_visible = True

    def search_button_pressed(self):
        """Focus search entry."""
        self.search_entry.grab_focus()

    def can_close_popover(self) -> bool:
        """If a pop-over menu is open, attempt to close it.

        Used by controller navigation to exit popovers.
        """
        if (focus_widget := self.props.focus_widget) and (
            popover_menu := focus_widget.get_ancestor(Gtk.PopoverMenu)
        ):
            popover_menu.popdown()
            return True
        return False

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

    def _get_focused_game(self) -> Gtk.Widget | None:
        if (focused_game := self.props.focus_widget) and focused_game.get_ancestor(
            Gtk.GridView
        ):
            return focused_game
        return None

    def _get_current_game_position(self) -> int:
        if (game_widget := self._get_focused_game()) and isinstance(
            item := game_widget.get_first_child(), GameItem
        ):
            return item.position
        return 0

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

    @Gtk.Template.Callback()
    def _update_selection(self, sidebar: Adw.Sidebar, *_args):
        if sidebar.props.selected_item is self.new_collection_item:
            sidebar.props.selected = self._selected_sidebar_item
        self._selected_sidebar_item = sidebar.props.selected

    @Gtk.Template.Callback()
    def _setup_sidebar_menu(self, _sidebar, item: Adw.SidebarItem):
        if isinstance(item, CollectionSidebarItem):
            self.menu_collection = item.collection

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
        self.grid.activate_action("list.activate-item", GLib.Variant("u", 0))

    @Gtk.Template.Callback()
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
