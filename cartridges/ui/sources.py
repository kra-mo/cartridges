# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from typing import Any

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import sources
from cartridges.sources import Source
from cartridges.ui import games


class SourceSidebarItem(Adw.SidebarItem):  # pyright: ignore[reportAttributeAccessIssue]
    """A sidebar item representing a source."""

    model = GObject.Property(type=Gio.ListModel)

    @GObject.Property(type=Source)
    def source(self) -> Source:
        """The source that `self` represents."""
        return self._source

    @source.setter
    def source(self, source: Source):
        self._source = source
        flags = GObject.BindingFlags.SYNC_CREATE
        source.bind_property("name", self, "title", flags)
        source.bind_property("icon-name", self, "icon-name", flags)

        self.model = Gtk.FilterListModel(
            model=source,
            filter=games.filter_,
            watch_items=True,  # pyright: ignore[reportCallIssue]
        )
        self.props.visible = self.model.props.n_items

    def __init__(self, source: Source, **kwargs: Any):
        super().__init__(**kwargs)

        # https://gitlab.gnome.org/GNOME/gtk/-/issues/7959
        self._model_signals = GObject.SignalGroup.new(Gio.ListModel)
        self._model_signals.connect_closure(
            "items-changed",
            lambda model, *_: self.set_property("visible", model.props.n_items),
            after=True,
        )
        self.bind_property("model", self._model_signals, "target")
        self.source = source


model = Gtk.SortListModel.new(
    sources.model,
    Gtk.StringSorter.new(Gtk.PropertyExpression.new(Source, None, "name")),
)
