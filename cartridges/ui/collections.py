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

    collection = GObject.Property(type=Collection)
    game = GObject.Property(type=Game)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.add_action_entries((
            ("add", lambda *_: add(self.game)),
            ("edit", lambda *_: edit(self.collection)),
            ("remove", lambda *_: remove(self.collection)),
        ))

        collection = Gtk.PropertyExpression.new(CollectionActions, None, "collection")
        has_collection = Gtk.ClosureExpression.new(bool, self._bool, (collection,))
        removed = Gtk.PropertyExpression.new(Collection, collection, "removed")
        not_removed = Gtk.ClosureExpression.new(bool, self._invert, (removed,))
        false = Gtk.ConstantExpression.new_for_value(False)

        edit_action = cast(Gio.SimpleAction, self.lookup_action("edit"))
        remove_action = cast(Gio.SimpleAction, self.lookup_action("remove"))

        has_collection.bind(edit_action, "enabled", self)
        Gtk.TryExpression.new((not_removed, false)).bind(remove_action, "enabled", self)

    @staticmethod
    def _bool(_, value: object) -> bool:
        return bool(value)

    @staticmethod
    def _invert(_, value: object) -> bool:
        return not value


class CollectionEditable(GObject.Object):
    """A helper object for editing a collection."""

    __gtype_name__ = __qualname__

    collection = GObject.Property(type=Collection)
    game = GObject.Property(type=Game)

    valid = GObject.Property(type=bool, default=False)

    name = GObject.Property(type=str)
    icon = GObject.Property(type=str)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        name = Gtk.PropertyExpression.new(CollectionEditable, None, "name")
        icon = Gtk.PropertyExpression.new(CollectionEditable, None, "icon")
        valid = Gtk.ClosureExpression.new(bool, self._all, (name, icon))
        valid.bind(self, "valid", self)

    def apply(self):
        """Apply the changes."""
        if not self.valid:
            return

        if not self.collection:
            game_ids = (self.game.game_id,) if self.game else ()
            self.collection = Collection(game_ids=game_ids)
            collections.model.append(self.collection)

        if self.collection.name != self.name:
            self.collection.name = self.name
            sorter.changed(Gtk.SorterChange.DIFFERENT)
        self.collection.icon = self.icon

        collections.save()

    @staticmethod
    def _all(_, *values: object) -> bool:
        return all(values)


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
    def do_match(self, item: GObject.Object | None = None) -> bool:
        if not (self.collection and isinstance(item, Game)):
            return True

        return item.game_id in self.collection

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self._collection_signals = GObject.SignalGroup(target_type=Collection)
        self._collection_signals.connect_closure(
            "items-changed",
            lambda *_: self.changed(Gtk.FilterChange.DIFFERENT),
            after=False,
        )
        self.bind_property("collection", self._collection_signals, "target")


class CollectionSidebarItem(Adw.SidebarItem):
    """A sidebar item representing a collection."""

    __gtype_name__ = __qualname__

    collection = GObject.Property(type=Collection)

    def __init__(self, collection: Collection | None = None, **kwargs: Any):
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

    __gtype_name__ = __qualname__

    collection = GObject.Property(type=Collection)

    def __init__(self, collection: Collection | None = None, **kwargs: Any):
        super().__init__(**kwargs)

        self.props.child = Adw.ButtonContent(can_shrink=True)

        flags = GObject.BindingFlags.DEFAULT
        self._collection_bindings = GObject.BindingGroup()
        self._collection_bindings.bind("name", self.props.child, "label", flags)
        self._collection_bindings.bind(
            "icon-name", self.props.child, "icon-name", flags
        )
        self.bind_property("collection", self._collection_bindings, "source")

        self.collection = collection


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
            collection = cast(Collection, button.collection)
            if button.props.active:
                collection.add(self.game.game_id)
            else:
                collection.discard(self.game.game_id)

        self.box.remove_all()


def add(game: Game | None = None):
    """Add a new collection, optionally with `game_id`."""
    from .collection_details import CollectionDetails

    details = CollectionDetails(game=game)
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
        watch_items=True,
    ),
    sorter=sorter,
)
