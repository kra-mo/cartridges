# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from typing import Any, cast

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import games
from cartridges.config import PREFIX
from cartridges.games import Collection

ICONS = (
    "collection-symbolic",
    "star-symbolic",
    "heart-symbolic",
    "music-symbolic",
    "people-symbolic",
    "skull-symbolic",
    "private-symbolic",
    "globe-symbolic",
    "map-symbolic",
    "city-symbolic",
    "car-symbolic",
    "horse-symbolic",
    "sprout-symbolic",
    "step-over-symbolic",
    "gamepad-symbolic",
    "ball-symbolic",
    "puzzle-symbolic",
    "flashlight-symbolic",
    "knife-symbolic",
    "gun-symbolic",
    "fist-symbolic",
)


@Gtk.Template.from_resource(f"{PREFIX}/collection-details.ui")
class CollectionDetails(Adw.Dialog):
    """The details of a category."""

    __gtype_name__ = __qualname__

    name_entry: Adw.EntryRow = Gtk.Template.Child()
    icons_box: Gtk.FlowBox = Gtk.Template.Child()

    collection = GObject.Property(type=Collection)

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

        icons = Gtk.StringList.new(ICONS)
        self.icons_box.bind_model(
            icons,
            lambda string: Gtk.FlowBoxChild(
                name="icon-child",
                child=Gtk.Image(
                    icon_name=string.props.string,
                    icon_size=Gtk.IconSize.NORMAL,
                ),
                halign=Gtk.Align.CENTER,
            ),
        )
        self.icons_box.select_child(
            cast(
                Gtk.FlowBoxChild,
                self.icons_box.get_child_at_index(
                    ICONS.index(self.collection.icon_name)
                ),
            )
        )

    def _apply(self):
        self.collection.name = self.name_entry.props.text
        self.collection.icon = ICONS[
            self.icons_box.get_selected_children()[0].get_index()
        ].removesuffix("-symbolic")

        if not self.collection.added:
            self.collection.added = True
            games.collections.append(self.collection)

        self.close()
