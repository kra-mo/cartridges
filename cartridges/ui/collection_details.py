# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

from itertools import product
from typing import Any, cast

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import collections
from cartridges.collections import ICONS, Collection
from cartridges.config import PREFIX

from . import closures
from .collections import CollectionActions, CollectionEditable

_COLUMNS = len(ICONS) // 3
_ROWS = len(ICONS) // _COLUMNS


@Gtk.Template(resource_path=f"{PREFIX}/collection-details.ui")
class CollectionDetails(Adw.Dialog):
    """The details of a category."""

    __gtype_name__ = __qualname__

    icons_grid: Gtk.Grid = Gtk.Template.Child()

    collection_actions: CollectionActions = Gtk.Template.Child()
    collection_editable: CollectionEditable = Gtk.Template.Child()
    collection_signals: GObject.SignalGroup = Gtk.Template.Child()

    either = closures.either
    if_else = closures.if_else
    on_change = closures.on_change
    within = closures.within

    @GObject.Property(type=Collection)
    def collection(self) -> Collection:
        """The collection that `self` represents."""
        return self._collection

    @collection.setter
    def collection(self, collection: Collection):
        self._collection = collection

        for index, icon in enumerate(icon.name for icon in ICONS):
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

        self.collection_editable.bind_property(
            "valid",
            cast(Gio.SimpleAction, group.lookup_action("apply")),
            "enabled",
            GObject.BindingFlags.SYNC_CREATE,
        )

        self.insert_action_group("collection", self.collection_actions)
        self.collection_signals.connect_closure(
            "notify::removed",
            lambda *_: self.force_close(),
            after=False,
        )

        group_button = None
        for index, (row, col) in enumerate(product(range(_ROWS), range(_COLUMNS))):
            icon = ICONS[index].name

            button = Gtk.ToggleButton(
                icon_name=f"{icon}-symbolic",
                hexpand=True,
                halign=Gtk.Align.CENTER,
            )
            button.update_property(
                (Gtk.AccessibleProperty.LABEL,), (ICONS[index].a11y_label,)
            )

            button.add_css_class("circular")
            button.add_css_class("flat")

            if group_button:
                button.props.group = group_button
            else:
                group_button = button

            button.connect(
                "toggled",
                lambda _, icon: self.collection_editable.set_property("icon", icon),
                icon,
            )

            self.icons_grid.attach(button, col, row, 1, 1)

        self.collection = collection or Collection()

    def _apply(self):
        self.collection_editable.apply()
        self.close()

    @Gtk.Template.Callback()
    def _collections(self, _obj) -> Gio.ListStore:
        return collections.model
