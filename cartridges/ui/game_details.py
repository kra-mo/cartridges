# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2022-2026 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel


import sys
from datetime import UTC, datetime
from gettext import gettext as _
from typing import Any, cast
from urllib.parse import quote

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from cartridges.games import Game

from .collections import CollectionActions, CollectionsBox
from .cover import Cover  # noqa: F401
from .games import GameActions, GameEditable
from .template import Child, template


@template
class GameDetails(Adw.NavigationPage):
    """The details of a game."""

    __gtype_name__ = __qualname__

    game = GObject.Property(type=Game)
    editing = GObject.Property(type=bool, default=False)

    collections_box: Child[CollectionsBox]
    name_entry: Child[Adw.EntryRow]

    game_actions: Child[GameActions]
    collection_actions: Child[CollectionActions]
    game_editable: Child[GameEditable]
    game_signals: Child[GObject.SignalGroup]

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
                    param.get_string().format(quote(cast(Game, self.game).name))
                ),
                "s",
            ),
        ))
        self.insert_action_group("details", group)

        self.game_editable.bind_property(
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
                after=False,
            )

    def add(self):
        """Add a new game."""
        self.game = None
        self.edit()

    def edit(self):
        """Enter edit mode."""
        self.editing = True
        self.name_entry.grab_focus()

    def _apply(self):
        self.game_editable.apply()
        self.game = self.game_editable.game
        self.editing = False

    def _activate_apply(self, _entry):
        self.activate_action("details.apply")

    def _cancel(self, *_args):
        if not (self.editing and self.game):
            self.activate_action("navigation.pop")
        self.editing = False

    def _setup_collections(self, button: Gtk.MenuButton, *_args):
        if button.props.active:
            self.collections_box.build()
        else:
            self.collections_box.finish()

    def _downscale_image(self, _obj, cover: Gdk.Paintable | None) -> Gdk.Texture | None:
        if cover and (renderer := cast(Gtk.Native, self.props.root).get_renderer()):
            cover.snapshot(snapshot := Gtk.Snapshot(), 3, 3)
            if node := snapshot.to_node():
                return renderer.render_texture(node)

        return None

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
