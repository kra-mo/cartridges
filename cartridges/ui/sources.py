# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from typing import Any

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import sources
from cartridges.sources import Source

from . import games


class SourceSidebarItem(Adw.SidebarItem):
    """A sidebar item representing a source."""

    __gtype_name__ = __qualname__

    source = GObject.Property(type=Source)
    model = GObject.Property(type=Gio.ListModel)

    def __init__(self, source: Source | None = None, **kwargs: Any):
        super().__init__(**kwargs)

        flags = GObject.BindingFlags.DEFAULT
        self._source_bindings = GObject.BindingGroup()
        self._source_bindings.bind("name", self, "title", flags)
        self._source_bindings.bind("icon-name", self, "icon-name", flags)
        self.bind_property("source", self._source_bindings, "source")

        self.model = Gtk.FilterListModel(filter=games.filter_, watch_items=True)
        self.model.bind_property(
            "n-items", self, "visible", GObject.BindingFlags.SYNC_CREATE
        )
        self.bind_property("source", self.model, "model")
        self.source = source


model = Gtk.SortListModel(
    model=sources.model,
    sorter=Gtk.StringSorter(
        expression=Gtk.PropertyExpression.new(Source, None, "name")
    ),
)
