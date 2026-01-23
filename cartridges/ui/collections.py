# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Iterable
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, cast, override

from gi.repository import Adw, Gio, GLib, GObject, Gtk

from cartridges import collections
from cartridges.collections import Collection
from cartridges.games import Game

if TYPE_CHECKING:
    from .window import Window


class CollectionActions(Gio.SimpleActionGroup):
    """Action group for collection actions."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)

    _collection: Collection | None = None

    @GObject.Property(type=Collection)
    def collection(self) -> Collection | None:
        """The collection `self` provides actions for."""
        return self._collection

    @collection.setter
    def collection(self, collection: Collection | None):
        self._collection = collection
        self._update_remove()

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.add_action_entries((
            ("add", lambda *_: add(self.game.game_id if self.game else None)),
            ("edit", lambda *_: edit(self.collection)),
            ("remove", lambda *_: remove(self.collection)),
        ))

        self.bind_property(
            "collection",
            cast(Gio.SimpleAction, self.lookup_action("edit")),
            "enabled",
            GObject.BindingFlags.SYNC_CREATE,
            transform_to=lambda _, collection: bool(collection),
        )

        self._collection_signals = GObject.SignalGroup(target_type=Collection)
        self._collection_signals.connect_closure(
            "notify::removed",
            lambda *_: self._update_remove(),
            after=False,
        )
        self._collection_signals.connect_closure(
            "notify::in-model",
            lambda *_: self._update_remove(),
            after=False,
        )
        self.bind_property("collection", self._collection_signals, "target")

        self._update_remove()

    def _update_remove(self):
        action = cast(Gio.SimpleAction, self.lookup_action("remove"))
        action.props.enabled = (
            self.collection and self.collection.in_model and not self.collection.removed
        )


class CollectionFilter(Gtk.Filter):
    """Filter games based on a selected collection."""

    __gtype_name__ = __qualname__

    @GObject.Property(type=Collection)
    def collection(self) -> Collection | None:
        """The collection used for filtering."""
        return self._collection

    @collection.setter
    def collection(self, collection: Collection | None):
        self._collection = collection
        self.changed(Gtk.FilterChange.DIFFERENT)

    @override
    def do_match(self, game: Game) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        if not self.collection:
            return True

        return game.game_id in self.collection

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self._collection_signals = GObject.SignalGroup(target_type=Collection)
        self._collection_signals.connect_closure(
            "items-changed",
            lambda *_: self.changed(Gtk.FilterChange.DIFFERENT),
            after=False,
        )
        self.bind_property("collection", self._collection_signals, "target")


class CollectionSidebarItem(Adw.SidebarItem):  # pyright: ignore[reportAttributeAccessIssue]
    """A sidebar item representing a collection."""

    collection = GObject.Property(type=Collection)

    def __init__(self, collection: Collection, **kwargs: Any):
        super().__init__(**kwargs)

        self.bind_property(
            "title",
            self,
            "tooltip",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _, name: GLib.markup_escape_text(name),
        )

        flags = GObject.BindingFlags.DEFAULT
        self._collection_bindings = GObject.BindingGroup()
        self._collection_bindings.bind("name", self, "title", flags)
        self._collection_bindings.bind("icon-name", self, "icon-name", flags)
        self.bind_property("collection", self._collection_bindings, "source")
        self.collection = collection


class CollectionButton(Gtk.ToggleButton):
    """A toggle button representing a collection."""

    collection = GObject.Property(type=Collection)

    def __init__(self, collection: Collection, **kwargs: Any):
        super().__init__(**kwargs)

        self.collection = collection
        self.props.child = Adw.ButtonContent(
            icon_name=collection.icon_name,
            label=collection.name,
            can_shrink=True,
        )


class CollectionsBox(Adw.Bin):
    """A wrap box for adding games to collections."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.props.child = self.box = Adw.WrapBox(
            child_spacing=6,
            line_spacing=6,
            justify=Adw.JustifyMode.FILL,
            justify_last_line=True,
            natural_line_length=240,
        )
        model.bind_property(
            "n-items",
            self,
            "visible",
            GObject.BindingFlags.SYNC_CREATE,
        )

    def build(self):
        """Populate the box with collections."""
        for collection in cast(Iterable[Collection], model):
            button = CollectionButton(collection)
            button.props.active = self.game.game_id in collection
            self.box.append(button)

    def finish(self):
        """Clear the box."""
        for button in cast(Iterable[CollectionButton], self.box):
            if button.props.active:
                button.collection.add(self.game.game_id)
            else:
                button.collection.discard(self.game.game_id)

        self.box.remove_all()  # pyright: ignore[reportAttributeAccessIssue]


def add(game_id: str | None = None):
    """Add a new collection, optionally with `game_id`."""
    from .collection_details import CollectionDetails

    collection = Collection(game_ids=filter(None, (game_id,)))
    details = CollectionDetails(collection)
    details.present(_window())


def edit(collection: Collection):
    """Edit `collection`."""
    from .collection_details import CollectionDetails

    details = CollectionDetails(collection)
    details.present(_window())


def remove(collection: Collection):
    """Remove `collection` and notify the user with a toast."""
    collection.removed = True
    _window().send_toast(
        _("{} removed").format(collection.name),
        undo=lambda: setattr(collection, "removed", False),
    )


def _window() -> "Window":
    app = cast(Gtk.Application, Gio.Application.get_default())
    return cast("Window", app.props.active_window)


sorter = Gtk.StringSorter(
    expression=Gtk.PropertyExpression.new(Collection, None, "name")
)
model = Gtk.SortListModel(
    model=Gtk.FilterListModel(
        model=collections.model,
        filter=Gtk.BoolFilter(
            expression=Gtk.PropertyExpression.new(Collection, None, "removed"),
            invert=True,
        ),
        watch_items=True,  # pyright: ignore[reportCallIssue]
    ),
    sorter=sorter,
)
