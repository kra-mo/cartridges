# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from typing import Any, override

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
