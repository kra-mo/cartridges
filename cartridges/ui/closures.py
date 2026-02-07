# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import sys
from collections.abc import Callable
from typing import Any

from gi.repository import Gtk


def _closure[**P, R](func: Callable[P, R]) -> object:  # gi._gtktemplate.CallThing
    @Gtk.Template.Callback()
    @staticmethod
    def wrapper(_obj, *args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)

    return wrapper


@_closure
def boolean(value: object) -> bool:
    """Get a boolean for `value`."""
    return bool(value)


@_closure
def either[T](first: T, second: T) -> T:
    """Return `first` or `second`."""
    return first or second


@_closure
def format_string(string: str, *args: Any) -> str:
    """Format `string` with `args`."""
    return string.format(*args)


@_closure
def if_else[T](condition: object, first: T, second: T) -> T:
    """Return `first` or `second` depending on `condition`."""
    return first if condition else second


@_closure
def shortcut(default: str, macos: str | None = None) -> Gtk.ShortcutTrigger | None:
    """Get the correct shortcut for the user's platform."""
    return Gtk.ShortcutTrigger.parse_string(
        (macos or default.replace("<Control>", "<Meta>"))
        if sys.platform.startswith("darwin")
        else default
    )
