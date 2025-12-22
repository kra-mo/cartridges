# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Iterable
from typing import Any, cast, override

from gi.repository import Adw, GObject, Gtk

from cartridges import collections
from cartridges.collections import Collection
from cartridges.games import Game


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

        return game.game_id in self.collection.game_ids


class CollectionSidebarItem(Adw.SidebarItem):  # pyright: ignore[reportAttributeAccessIssue]
    """A sidebar item representing a collection."""

    @GObject.Property(type=Collection)
    def collection(self) -> Collection:
        """The collection that `self` represents."""
        return self._collection

    @collection.setter
    def collection(self, collection: Collection):
        self._collection = collection
        flags = GObject.BindingFlags.SYNC_CREATE
        collection.bind_property("name", self, "title", flags)
        collection.bind_property("icon-name", self, "icon-name", flags)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.bind_property("title", self, "tooltip", GObject.BindingFlags.SYNC_CREATE)


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
            button.props.active = self.game.game_id in collection.game_ids
            self.box.append(button)

    def finish(self):
        """Clear the box and save changes."""
        filter_changed = False
        for button in cast(Iterable[CollectionButton], self.box):
            game_ids = button.collection.game_ids
            old_game_ids = game_ids.copy()
            in_collection = self.game.game_id in game_ids

            if button.props.active and not in_collection:
                game_ids.append(self.game.game_id)
            elif not button.props.active and in_collection:
                game_ids.remove(self.game.game_id)

            if game_ids != old_game_ids:
                filter_changed = True

        self.box.remove_all()  # pyright: ignore[reportAttributeAccessIssue]
        collections.save()

        if filter_changed:
            self.activate_action("win.notify-collection-filter")


sorter = Gtk.StringSorter.new(Gtk.PropertyExpression.new(Collection, None, "name"))
model = Gtk.SortListModel.new(
    Gtk.FilterListModel(
        model=collections.model,
        filter=Gtk.BoolFilter(
            expression=Gtk.PropertyExpression.new(Collection, None, "removed"),
            invert=True,
        ),
        watch_items=True,  # pyright: ignore[reportCallIssue]
    ),
    sorter,
)
