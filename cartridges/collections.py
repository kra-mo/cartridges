# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from typing import Any

from gi.repository import Gio, GObject


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


model = Gio.ListStore.new(Collection)
