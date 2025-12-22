# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

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
    icons_box: Gtk.FlowBox = Gtk.Template.Child()

    sort_changed = GObject.Signal()

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

        icons = Gtk.StringList.new(tuple(f"{icon}-symbolic" for icon in ICONS))
        self.icons_box.bind_model(
            icons,
            lambda string: Gtk.FlowBoxChild(
                name="collection-icon-child",
                child=Gtk.Image.new_from_icon_name(string.props.string),
                halign=Gtk.Align.CENTER,
            ),
        )
        self.icons_box.select_child(
            cast(
                Gtk.FlowBoxChild,
                self.icons_box.get_child_at_index(ICONS.index(self.collection.icon)),
            )
        )

    def _apply(self):
        name = self.name_entry.props.text
        if self.collection.name != name:
            self.collection.name = name
            if self.collection.in_model:
                self.emit("sort-changed")

        self.collection.icon = ICONS[
            self.icons_box.get_selected_children()[0].get_index()
        ]

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
