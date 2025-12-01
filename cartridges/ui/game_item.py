# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from gi.repository import GObject, Gtk

from cartridges.config import PREFIX
from cartridges.games import Game

from .cover import Cover  # noqa: F401


@Gtk.Template.from_resource(f"{PREFIX}/game-item.ui")
class GameItem(Gtk.Box):
    """A game in the grid."""

    __gtype_name__ = __qualname__

    @GObject.Property(type=Game)
    def game(self) -> Game | None:
        """The game that `self` represents."""
        return self._game

    @game.setter
    def game(self, game: Game | None):
        self._game = game
        self.insert_action_group("game", game)

    @Gtk.Template.Callback()
    def _any(self, _obj, *values: bool) -> bool:
        return any(values)
