# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Generator
from typing import Any

from gi.repository import Gio, GObject

from cartridges import SETTINGS


class Collection(GObject.Object):
    """Collection data class."""

    __gtype_name__ = __qualname__

    name = GObject.Property(type=str)
    icon = GObject.Property(type=str, default="collection")
    game_ids = GObject.Property(type=object)
    removed = GObject.Property(type=bool, default=False)

    icon_name = GObject.Property(type=str)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.game_ids = []
        self.bind_property(
            "icon",
            self,
            "icon-name",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _, name: f"{name}-symbolic",
        )


def _get_collections() -> Generator[Collection]:
    for data in SETTINGS.get_value("collections").unpack():
        if data.get("removed"):
            continue

        collection = Collection()
        for prop, value in data.items():
            try:
                collection.set_property(prop, value)
            except TypeError:
                continue

        yield collection


def load():
    """Load collections from GSettings."""
    model.splice(0, 0, tuple(_get_collections()))


model = Gio.ListStore.new(Collection)
