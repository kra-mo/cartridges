# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Generator, Iterable, Iterator
from typing import Any, cast

from gi.repository import Gio, GLib, GObject

from cartridges import SETTINGS
from cartridges.sources import imported

type _GameID = str


class Collection(GObject.Object):
    """Collection data class.

    Changes to `removed` and the game IDs are autosaved.

    Changes to `name` and `icon` require explicit saving with `collections.save()`.
    """

    __gtype_name__ = __qualname__

    name = GObject.Property(type=str)
    icon = GObject.Property(type=str, default="collection")
    removed = GObject.Property(type=bool, default=False)

    icon_name = GObject.Property(type=str)

    items_changed = GObject.Signal()

    @GObject.Property(type=bool, default=False)
    def in_model(self) -> bool:
        """Whether `self` has been added to the model."""
        return self in model

    def __init__(self, *, game_ids: Iterable[_GameID] = (), **kwargs: Any):
        super().__init__(**kwargs)

        self._game_ids = set(game_ids)

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
            after=False,
        )
        self._model_signals.props.target = model

        for signal in "items-changed", "notify::removed":
            self.connect(signal, lambda *_: save())

    def __iter__(self) -> Iterator[_GameID]:
        return iter(self._game_ids)

    def __contains__(self, game_id: _GameID) -> bool:
        return game_id in self._game_ids

    def add(self, game_id: _GameID):
        """Add `game_id` if not present."""
        if game_id not in self:
            self._game_ids.add(game_id)
            self.emit("items-changed")

    def discard(self, game_id: _GameID):
        """Discard `game_id` if present."""
        if game_id in self:
            self._game_ids.discard(game_id)
            self.emit("items-changed")


def load():
    """Load collections from GSettings."""
    model.splice(0, 0, tuple(_get_collections()))


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
                    "game-ids": GLib.Variant.new_strv(tuple(collection)),
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
                game_ids=(
                    ident
                    for ident in data["game-ids"]
                    if not ident.startswith(imported.ID) or ident in imported_ids
                ),
            )
        except (KeyError, TypeError):
            continue


model = Gio.ListStore.new(Collection)
model.connect("items-changed", lambda *_: save())
