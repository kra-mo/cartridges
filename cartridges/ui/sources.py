# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Generator
from typing import Any, override

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import SETTINGS
from cartridges.games import Game
from cartridges.sources import heroic, steam


class Source(GObject.Object):
    """GObject wrapper for sources."""

    __gtype_name__ = __qualname__

    id = GObject.Property(type=str)
    name = GObject.Property(type=str)
    icon_name = GObject.Property(type=str)
    enabled = GObject.Property(type=bool, default=True)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.icon_name = f"{self.id}-symbolic"
        SETTINGS.bind(self.id, self, "enabled", Gio.SettingsBindFlags.DEFAULT)


class SourceFilter(Gtk.Filter):
    """Filter games based on a selected source."""

    __gtype_name__ = __qualname__

    @GObject.Property(type=Source)
    def source(self) -> Source | None:
        """The source used for filtering."""
        return self._source

    @source.setter
    def source(self, source: Source | None):
        self._source = source
        self.changed(Gtk.FilterChange.DIFFERENT)

    @override
    def do_match(self, game: Game) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        if not self.source:
            return True

        return game.source.startswith(self.source.id)


class SourceSidebarItem(Adw.SidebarItem):  # pyright: ignore[reportAttributeAccessIssue]
    """A sidebar item representing a collection."""

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
        source.bind_property("enabled", self, "visible", flags)


def _get_sources() -> Generator[Source]:
    for source in heroic, steam:
        yield Source(id=source.ID, name=source.NAME)


def load():
    """Load `Source`s from `sources.Source`s."""
    model.splice(0, 0, tuple(_get_sources()))


model = Gio.ListStore.new(Source)
