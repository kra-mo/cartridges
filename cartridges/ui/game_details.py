# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2022-2025 kramo


import sys
from datetime import UTC, datetime
from gettext import gettext as _
from typing import Any, cast
from urllib.parse import quote

from gi.repository import Adw, Gdk, Gio, GObject, Gtk

from cartridges.config import PREFIX
from cartridges.games import Game

from .cover import Cover  # noqa: F401

_EDITABLE_PROPERTIES = "name", "developer", "executable"


@Gtk.Template.from_resource(f"{PREFIX}/game-details.ui")
class GameDetails(Adw.NavigationPage):
    """The details of a game."""

    __gtype_name__ = __qualname__

    stack: Adw.ViewStack = Gtk.Template.Child()
    name_entry: Adw.EntryRow = Gtk.Template.Child()
    developer_entry: Adw.EntryRow = Gtk.Template.Child()
    executable_entry: Adw.EntryRow = Gtk.Template.Child()

    sort_changed = GObject.Signal()

    @GObject.Property(type=Game)
    def game(self) -> Game | None:
        """The game whose details to show."""
        return self._game

    @game.setter
    def game(self, game: Game | None):
        self._game = game
        self.insert_action_group("game", game)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.insert_action_group("details", group := Gio.SimpleActionGroup())
        group.add_action_entries((
            ("edit", lambda *_: self.edit()),
            ("edit-done", lambda *_: self.edit_done()),
            (
                "search-on",
                lambda _action, param, *_: Gio.AppInfo.launch_default_for_uri(
                    param.get_string().format(quote(self.game.name))
                ),
                "s",
            ),
        ))

    def edit(self):
        """Enter edit mode."""
        for prop in _EDITABLE_PROPERTIES:
            getattr(self, f"{prop}_entry").props.text = getattr(self.game, prop)

        self.stack.props.visible_child_name = "edit"
        self.name_entry.grab_focus()

    def edit_done(self):
        """Save edits and exit edit mode."""
        if self.stack.props.visible_child_name != "edit":
            return

        for prop in _EDITABLE_PROPERTIES:
            text = getattr(self, f"{prop}_entry").props.text
            if text != getattr(self.game, prop) and (text or prop == "developer"):
                setattr(self.game, prop, text)
                if prop == "name":
                    self.emit("sort-changed")

        self.stack.props.visible_child_name = "details"

    @Gtk.Template.Callback()
    def _downscale_image(self, _obj, cover: Gdk.Texture | None) -> Gdk.Texture | None:
        if cover and (renderer := cast(Gtk.Native, self.props.root).get_renderer()):
            cover.snapshot(snapshot := Gtk.Snapshot.new(), 3, 3)
            if node := snapshot.to_node():
                return renderer.render_texture(node)

        return None

    @Gtk.Template.Callback()
    def _date_label(self, _obj, label: str, timestamp: int) -> str:
        date = datetime.fromtimestamp(timestamp, UTC)
        now = datetime.now(UTC)
        return label.format(
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
    def _bool(self, _obj, o: object) -> bool:
        return bool(o)

    @Gtk.Template.Callback()
    def _pop(self, _obj):
        self.activate_action("navigation.pop")

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
