# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import locale
from gettext import gettext as _
from typing import TYPE_CHECKING, Any, cast

from gi.repository import Gio, GObject, Gtk

from cartridges import STATE_SETTINGS, sources
from cartridges.games import Game
from cartridges.sources import imported

if TYPE_CHECKING:
    from .window import Window

_SORT_MODES = {
    "last_played": ("last-played", True),
    "a-z": ("name", False),
    "z-a": ("name", True),
    "newest": ("added", True),
    "oldest": ("added", False),
}


class GameActions(Gio.SimpleActionGroup):
    """Action group for game actions."""

    __gtype_name__ = __qualname__

    _game: Game | None = None

    @GObject.Property(type=Game)
    def game(self) -> Game | None:
        """The game `self` provides actions for."""
        return self._game

    @game.setter
    def game(self, game: Game | None):
        self._game = game
        self._update_action_states()

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        self.add_action_entries((
            ("add", lambda *_: add()),
            ("edit", lambda *_: edit(self.game)),
            ("play", lambda *_: self.game.play()),
            ("hide", lambda *_: hide(self.game)),
            ("unhide", lambda *_: unhide(self.game)),
            ("remove", lambda *_: remove(self.game)),
        ))

        for name in "edit", "play":
            self.bind_property(
                "game",
                cast(Gio.SimpleAction, self.lookup_action(name)),
                "enabled",
                GObject.BindingFlags.SYNC_CREATE,
                transform_to=lambda _, game: bool(game),
            )

        self._game_bindings = GObject.BindingGroup()
        self._game_bindings.bind(
            "hidden",
            cast(Gio.SimpleAction, self.lookup_action("hide")),
            "enabled",
            GObject.BindingFlags.INVERT_BOOLEAN,
        )
        self._game_bindings.bind(
            "hidden",
            cast(Gio.SimpleAction, self.lookup_action("unhide")),
            "enabled",
            GObject.BindingFlags.DEFAULT,
        )
        self._game_bindings.bind(
            "removed",
            cast(Gio.SimpleAction, self.lookup_action("remove")),
            "enabled",
            GObject.BindingFlags.INVERT_BOOLEAN,
        )
        self.bind_property("game", self._game_bindings, "source")

        self._update_action_states()

    def _update_action_states(self):
        if not self.game:
            for name in "hide", "unhide", "remove":
                action = cast(Gio.SimpleAction, self.lookup_action(name))
                action.props.enabled = False


def add():
    """Add a new game."""
    window = _window()
    window.details.game = imported.new()

    if window.navigation_view.props.visible_page_tag != "details":
        window.navigation_view.push_by_tag("details")

    window.details.edit()


def edit(game: Game):
    """Edit `game`."""
    window = _window()
    window.details.game = game
    window.navigation_view.push_by_tag("details")
    window.details.edit()


def hide(game: Game):
    """Hide `game` and notify the user with a toast."""
    game.hidden = True
    _window().send_toast(
        _("{} hidden").format(game.name),
        undo=lambda: setattr(game, "hidden", False),
    )


def unhide(game: Game):
    """Unhide `game` and notify the user with a toast."""
    game.hidden = False
    _window().send_toast(
        _("{} unhidden").format(game.name),
        undo=lambda: setattr(game, "hidden", True),
    )


def remove(game: Game):
    """Remove `game` and notify the user with a toast."""
    game.removed = True
    _window().send_toast(
        _("{} removed").format(game.name),
        undo=lambda: setattr(game, "removed", False),
    )


def _window() -> "Window":
    app = cast(Gtk.Application, Gio.Application.get_default())
    return cast("Window", app.props.active_window)


def _sort(game1: Game, game2: Game) -> int:
    prop, invert = _SORT_MODES[STATE_SETTINGS.get_string("sort-mode")]
    a = (game2 if invert else game1).get_property(prop)
    b = (game1 if invert else game2).get_property(prop)

    return (
        _name_cmp(a, b)
        if isinstance(a, str)
        else ((a > b) - (a < b)) or _name_cmp(game1.name, game2.name)
    )


def _name_cmp(a: str, b: str) -> int:
    a, b = (name.lower().removeprefix("the ") for name in (a, b))
    return locale.strcoll(a, b)


filter_ = Gtk.EveryFilter()
filter_.append(
    Gtk.BoolFilter(
        expression=Gtk.PropertyExpression.new(Game, None, "removed"),
        invert=True,
    )
)
filter_.append(
    Gtk.BoolFilter(
        expression=Gtk.PropertyExpression.new(Game, None, "blacklisted"),
        invert=True,
    )
)

sorter = Gtk.CustomSorter.new(lambda game1, game2, _: _sort(game1, game2))
STATE_SETTINGS.connect(
    "changed::sort-mode", lambda *_: sorter.changed(Gtk.SorterChange.DIFFERENT)
)

model = Gtk.SortListModel(
    model=Gtk.FilterListModel(
        model=Gtk.FlattenListModel(model=sources.model),
        filter=filter_,
        watch_items=True,  # pyright: ignore[reportCallIssue]
    ),
    sorter=sorter,
)
