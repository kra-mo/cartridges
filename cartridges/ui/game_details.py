# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel


import sys
import time
from datetime import UTC, datetime
from gettext import gettext as _
from typing import Any, cast
from urllib.parse import quote

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from cartridges import games, sources
from cartridges.config import PREFIX
from cartridges.games import Game
from cartridges.sources import imported
from cartridges.ui import closures

from .collections import CollectionActions, CollectionsBox
from .cover import Cover  # noqa: F401
from .games import GameActions

_EDITABLE_PROPERTIES = {prop.name for prop in games.PROPERTIES if prop.editable}
_REQUIRED_PROPERTIES = {
    prop.name for prop in games.PROPERTIES if prop.editable and prop.required
}


@Gtk.Template.from_resource(f"{PREFIX}/game-details.ui")
class GameDetails(Adw.NavigationPage):
    """The details of a game."""

    __gtype_name__ = __qualname__

    stack: Adw.ViewStack = Gtk.Template.Child()
    collections_box: CollectionsBox = Gtk.Template.Child()
    name_entry: Adw.EntryRow = Gtk.Template.Child()

    game_actions: GameActions = Gtk.Template.Child()
    collection_actions: CollectionActions = Gtk.Template.Child()
    game_signals: GObject.SignalGroup = Gtk.Template.Child()

    game = GObject.Property(type=Game)

    valid = GObject.Property(type=bool, default=False)
    game_name = GObject.Property(type=str)
    game_developer = GObject.Property(type=str)
    game_executable = GObject.Property(type=str)

    sort_changed = GObject.Signal()

    boolean = closures.boolean
    either = closures.either
    every = closures.every
    format_string = closures.format_string
    if_else = closures.if_else

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        group = Gio.SimpleActionGroup()
        group.add_action_entries((
            ("edit", lambda *_: self.edit()),
            ("cancel", lambda *_: self._cancel()),
            ("apply", lambda *_: self._apply()),
            (
                "search-on",
                lambda _action, param, *_: Gio.AppInfo.launch_default_for_uri(
                    param.get_string().format(quote(self.game.name))
                ),
                "s",
            ),
        ))
        self.insert_action_group("details", group)

        self.bind_property(
            "valid",
            cast(Gio.SimpleAction, group.lookup_action("apply")),
            "enabled",
            GObject.BindingFlags.SYNC_CREATE,
        )

        self.insert_action_group("game", self.game_actions)
        self.insert_action_group("collection", self.collection_actions)

        for name in "hidden", "removed":
            self.game_signals.connect_closure(
                f"notify::{name}",
                lambda *_: self.activate_action("navigation.pop"),
                after=True,
            )

    def edit(self):
        """Enter edit mode."""
        for prop in _EDITABLE_PROPERTIES:
            value = getattr(self.game, prop)
            setattr(self, f"game_{prop}", value)

        self.stack.props.visible_child_name = "edit"
        self.name_entry.grab_focus()

    def _apply(self):
        for prop in _EDITABLE_PROPERTIES:
            value = getattr(self, f"game_{prop}")
            previous_value = getattr(self.game, prop)

            if value != previous_value:
                setattr(self.game, prop, value)
                if prop == "name" and self.game.added:
                    self.emit("sort-changed")

        if not self.game.added:
            self.game.added = int(time.time())
            sources.get(imported.ID).append(self.game)

        self.stack.props.visible_child_name = "details"

    @Gtk.Template.Callback()
    def _activate_apply(self, _entry):
        self.activate_action("details.apply")

    @Gtk.Template.Callback()
    def _cancel(self, *_args):
        if self.stack.props.visible_child_name == "details" or not self.game.added:
            self.activate_action("navigation.pop")

        self.stack.props.visible_child_name = "details"

    @Gtk.Template.Callback()
    def _setup_collections(self, button: Gtk.MenuButton, *_args):
        if button.props.active:
            self.collections_box.build()
        else:
            self.collections_box.finish()

    @Gtk.Template.Callback()
    def _downscale_image(self, _obj, cover: Gdk.Texture | None) -> Gdk.Texture | None:
        if cover and (renderer := cast(Gtk.Native, self.props.root).get_renderer()):
            cover.snapshot(snapshot := Gtk.Snapshot.new(), 3, 3)
            if node := snapshot.to_node():
                return renderer.render_texture(node)

        return None

    @Gtk.Template.Callback()
    def _relative_date(self, _obj, timestamp: int) -> str:
        date = datetime.fromtimestamp(timestamp, UTC)
        now = datetime.now(UTC)
        return (
            _("Never")
            if not timestamp
            else _("Today")
            if (n_days := (now - date).days) == 0
            else _("Yesterday")
            if n_days == 1
            else date.strftime("%A")
            if n_days <= (day_of_week := now.weekday())
            else _("Last Week")
            if n_days <= day_of_week + 7
            else _("This Month")
            if n_days <= (day_of_month := now.day)
            else _("Last Month")
            if n_days <= day_of_month + 30
            else date.strftime("%B")
            if n_days < (day_of_year := now.timetuple().tm_yday)
            else _("Last Year")
            if n_days <= day_of_year + 365
            else date.strftime("%Y")
        )

    @Gtk.Template.Callback()
    def _format_more_info(self, _obj, label: str) -> str:
        executable = _("program")
        filename = _("file.txt")
        path = _("/path/to/{}")
        command = "xdg-open"

        if sys.platform.startswith("darwin"):
            command = "open"
        elif sys.platform.startswith("win32"):
            executable += ".exe"
            path = _(r"C:\path\to\{}")
            command = "start"

        return label.format(
            executable,
            path.format(executable),
            filename,
            command,
            path.format(filename),
        )
