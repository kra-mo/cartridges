# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from itertools import product
from typing import Any, NamedTuple, cast

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import collections
from cartridges.collections import Collection
from cartridges.config import PREFIX

from . import closures
from .collections import CollectionActions


class _Icon(NamedTuple):
    name: str
    a11y_label: str


_ICONS = (
    _Icon("collection", "📚"),
    _Icon("star", "⭐"),
    _Icon("heart", "❤️"),
    _Icon("music", "🎵"),
    _Icon("people", "🧑"),
    _Icon("skull", "💀"),
    _Icon("private", "🕵️"),
    _Icon("globe", "🌐"),
    _Icon("map", "🗺"),
    _Icon("city", "🏙️"),
    _Icon("car", "🚗"),
    _Icon("horse", "🐎"),
    _Icon("sprout", "🌱"),
    _Icon("step-over", "🪜"),
    _Icon("gamepad", "🎮"),
    _Icon("ball", "⚽"),
    _Icon("puzzle", "🧩"),
    _Icon("flashlight", "🔦"),
    _Icon("knife", "🔪"),
    _Icon("gun", "🔫"),
    _Icon("fist", "✊"),
)

_COLUMNS = 7
_ROWS = 3


@Gtk.Template(resource_path=f"{PREFIX}/collection-details.ui")
class CollectionDetails(Adw.Dialog):
    """The details of a category."""

    __gtype_name__ = __qualname__

    icons_grid: Gtk.Grid = Gtk.Template.Child()

    collection_actions: CollectionActions = Gtk.Template.Child()
    collection_signals: GObject.SignalGroup = Gtk.Template.Child()
    collection_bindings: GObject.BindingGroup = Gtk.Template.Child()

    collection_name = GObject.Property(type=str)
    collection_icon = GObject.Property(type=str)

    sort_changed = GObject.Signal()

    either = closures.either
    if_else = closures.if_else

    @GObject.Property(type=Collection)
    def collection(self) -> Collection:
        """The collection that `self` represents."""
        return self._collection

    @collection.setter
    def collection(self, collection: Collection):
        self._collection = collection

        for index, icon in enumerate(icon.name for icon in _ICONS):
            if icon == collection.icon:
                button = cast(
                    Gtk.ToggleButton,
                    self.icons_grid.get_child_at(*reversed(divmod(index, _COLUMNS))),
                )
                button.props.active = True
                break

    def __init__(self, collection: Collection | None = None, **kwargs: Any):
        super().__init__(**kwargs)

        group = Gio.SimpleActionGroup()
        group.add_action_entries((("apply", lambda *_: self._apply()),))
        self.insert_action_group("details", group)

        self.bind_property(
            "collection-name",
            cast(Gio.SimpleAction, group.lookup_action("apply")),
            "enabled",
            transform_to=lambda _, name: bool(name),
        )

        self.insert_action_group("collection", self.collection_actions)
        self.collection_signals.connect_closure(
            "notify::removed",
            lambda *_: self.force_close(),
            after=False,
        )
        self.collection_bindings.bind(
            "name",
            self,
            "collection-name",
            GObject.BindingFlags.DEFAULT,
        )

        group_button = None
        for index, (row, col) in enumerate(product(range(_ROWS), range(_COLUMNS))):
            icon = _ICONS[index].name

            button = Gtk.ToggleButton(
                icon_name=f"{icon}-symbolic",
                hexpand=True,
                halign=Gtk.Align.CENTER,
            )
            button.update_property(
                (Gtk.AccessibleProperty.LABEL,), (_ICONS[index].a11y_label,)
            )

            button.add_css_class("circular")
            button.add_css_class("flat")

            if group_button:
                button.props.group = group_button
            else:
                group_button = button

            button.connect(
                "toggled",
                lambda _, icon: setattr(self, "collection_icon", icon),
                icon,
            )

            self.icons_grid.attach(button, col, row, 1, 1)

        self.collection = collection or Collection()

    def _apply(self):
        if self.collection.name != self.collection_name:
            self.collection.name = self.collection_name
            if self.collection.in_model:
                self.emit("sort-changed")

        self.collection.icon = self.collection_icon

        if self.collection.in_model:
            collections.save()
        else:
            collections.model.append(self.collection)

        self.close()
