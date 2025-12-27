# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from itertools import product
from typing import Any, TypeVar, cast

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import collections
from cartridges.collections import Collection
from cartridges.config import PREFIX

ICONS = (
    "collection",
    "star",
    "heart",
    "music",
    "people",
    "skull",
    "private",
    "globe",
    "map",
    "city",
    "car",
    "horse",
    "sprout",
    "step-over",
    "gamepad",
    "ball",
    "puzzle",
    "flashlight",
    "knife",
    "gun",
    "fist",
)

_T = TypeVar("_T")


@Gtk.Template.from_resource(f"{PREFIX}/collection-details.ui")
class CollectionDetails(Adw.Dialog):
    """The details of a category."""

    __gtype_name__ = __qualname__

    name_entry: Adw.EntryRow = Gtk.Template.Child()
    icons_grid: Gtk.Grid = Gtk.Template.Child()

    sort_changed = GObject.Signal()

    _selected_icon: str

    @GObject.Property(type=Collection)
    def collection(self) -> Collection:
        """The collection that `self` represents."""
        return self._collection

    @collection.setter
    def collection(self, collection: Collection):
        self._collection = collection
        self.insert_action_group("collection", collection)
        remove_action = cast(Gio.SimpleAction, collection.lookup_action("remove"))
        remove_action.connect("activate", lambda *_: self.force_close())

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.insert_action_group("details", group := Gio.SimpleActionGroup())

        group.add_action(apply := Gio.SimpleAction.new("apply"))
        apply.connect("activate", lambda *_: self._apply())
        self.name_entry.bind_property(
            "text",
            apply,
            "enabled",
            GObject.BindingFlags.SYNC_CREATE,
            transform_to=lambda _, text: bool(text),
        )

        group_button = None
        for index, (row, col) in enumerate(product(range(3), range(7))):
            icon = ICONS[index]

            button = Gtk.ToggleButton(
                icon_name=f"{icon}-symbolic",
                hexpand=True,
                halign=Gtk.Align.CENTER,
            )
            button.add_css_class("circular")
            button.add_css_class("flat")

            if group_button:
                button.props.group = group_button
            else:
                group_button = button

            button.connect(
                "toggled",
                lambda _, icon: setattr(self, "_selected_icon", icon),
                icon,
            )

            if icon == self.collection.icon:
                button.props.active = True

            self.icons_grid.attach(button, col, row, 1, 1)

    def _apply(self):
        name = self.name_entry.props.text
        if self.collection.name != name:
            self.collection.name = name
            if self.collection.in_model:
                self.emit("sort-changed")

        self.collection.icon = self._selected_icon

        if not self.collection.in_model:
            collections.model.append(self.collection)
            self.collection.notify("in-model")

        collections.save()
        self.close()

    @Gtk.Template.Callback()
    def _or(self, _obj, first: _T, second: _T) -> _T:
        return first or second

    @Gtk.Template.Callback()
    def _if_else(self, _obj, condition: object, first: _T, second: _T) -> _T:
        return first if condition else second
