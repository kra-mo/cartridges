# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from collections.abc import Generator, Iterable
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, cast

from gi.repository import Gio, GLib, GObject

from cartridges import SETTINGS

if TYPE_CHECKING:
    from .application import Application
    from .ui.window import Window


class Collection(Gio.SimpleActionGroup):
    """Collection data class."""

    __gtype_name__ = __qualname__

    name = GObject.Property(type=str)
    icon = GObject.Property(type=str, default="collection")
    game_ids = GObject.Property(type=object)
    removed = GObject.Property(type=bool, default=False)

    icon_name = GObject.Property(type=str)

    @GObject.Property(type=bool, default=True)
    def in_model(self) -> bool:
        """Whether `self` has been added to the model."""
        return self in model

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

        self.add_action(remove := Gio.SimpleAction.new("remove"))
        remove.connect("activate", lambda *_: self._remove())
        self.bind_property(
            "in-model",
            remove,
            "enabled",
            GObject.BindingFlags.SYNC_CREATE,
        )

    def _remove(self):
        self.removed = True
        save()

        app = cast("Application", Gio.Application.get_default())
        window = cast("Window", app.props.active_window)
        window.send_toast(_("{} removed").format(self.name), undo=self._undo_remove)

    def _undo_remove(self):
        self.removed = False
        save()


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
    save()

    for collection in model:
        collection.notify("in-model")


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
                    "game-ids": GLib.Variant.new_strv(collection.game_ids),
                    "removed": GLib.Variant.new_boolean(collection.removed),
                }
                for collection in cast(Iterable[Collection], model)
            ),
        ),
    )


model = Gio.ListStore.new(Collection)
