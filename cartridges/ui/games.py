# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import locale
from typing import Any, override

from gi.repository import Gtk

from cartridges import STATE_SETTINGS
from cartridges.games import Game

_SORT_MODES = {
    "last_played": ("last-played", True),
    "a-z": ("name", False),
    "z-a": ("name", True),
    "newest": ("added", True),
    "oldest": ("added", False),
}


class GameSorter(Gtk.Sorter):
    """A sorter for game objects.

    Automatically updates if the "sort-mode" GSetting changes.
    """

    __gtype_name__ = __qualname__

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

        STATE_SETTINGS.connect(
            "changed::sort-mode", lambda *_: self.changed(Gtk.SorterChange.DIFFERENT)
        )

    @override
    def do_compare(self, game1: Game, game2: Game) -> Gtk.Ordering:  # pyright: ignore[reportIncompatibleMethodOverride]
        prop, invert = _SORT_MODES[STATE_SETTINGS.get_string("sort-mode")]
        a = (game2 if invert else game1).get_property(prop)
        b = (game1 if invert else game2).get_property(prop)

        return Gtk.Ordering(
            self._name_cmp(a, b)
            if isinstance(a, str)
            else ((a > b) - (a < b)) or self._name_cmp(game1.name, game2.name)
        )

    @staticmethod
    def _name_cmp(a: str, b: str) -> int:
        a, b = (name.lower().removeprefix("the ") for name in (a, b))
        return max(-1, min(locale.strcoll(a, b), 1))
