# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Generator, Iterable
from typing import Any, cast

from gi.repository import Gio, GLib, GObject

from cartridges import SETTINGS
from cartridges.sources import imported


class Collection(GObject.Object):
    """Collection data class."""

    __gtype_name__ = __qualname__

    name = GObject.Property(type=str)
    icon = GObject.Property(type=str, default="collection")
    game_ids = GObject.Property(type=object)
    removed = GObject.Property(type=bool, default=False)

    icon_name = GObject.Property(type=str)

    @GObject.Property(type=bool, default=False)
    def in_model(self) -> bool:
        """Whether `self` has been added to the model."""
        return self in model

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.game_ids = self.game_ids or set()
        self.bind_property(
            "icon",
            self,
            "icon-name",
            GObject.BindingFlags.SYNC_CREATE,
            lambda _, name: f"{name}-symbolic",
        )

        self._model_signals = GObject.SignalGroup.new(Gio.ListModel)
        self._model_signals.connect_closure(
            "items-changed",
            lambda *_: self.notify("in-model"),
            after=True,
        )
        self._model_signals.props.target = model


def load():
    """Load collections from GSettings."""
    model.splice(0, 0, tuple(_get_collections()))
    save()


def save():
    """Save collections to GSettings."""
    SETTINGS.set_value(
        "collections",
        GLib.Variant(
            "aa{sv}",
            (
                {
                    "name": GLib.Variant.new_string(collection.name),
                    "icon": GLib.Variant.new_string(collection.icon),
                    "game-ids": GLib.Variant.new_strv(tuple(collection.game_ids)),
                    "removed": GLib.Variant.new_boolean(collection.removed),
                }
                for collection in cast(Iterable[Collection], model)
            ),
        ),
    )


def _get_collections() -> Generator[Collection]:
    imported_ids = {p.stem for p in imported.get_paths()}
    for data in SETTINGS.get_value("collections").unpack():
        if data.get("removed"):
            continue

        try:
            yield Collection(
                name=data["name"],
                icon=data["icon"],
                game_ids={
                    ident
                    for ident in data["game-ids"]
                    if not ident.startswith(imported.ID) or ident in imported_ids
                },
            )
        except (KeyError, TypeError):
            continue


model = Gio.ListStore.new(Collection)
