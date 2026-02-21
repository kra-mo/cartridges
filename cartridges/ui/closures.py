# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import functools
import sys
from collections.abc import Callable
from typing import Any, Concatenate

from gi.repository import Gtk

closures: dict[str, Callable[..., Any]] = {}


def closure[**P, R](func: Callable[P, R]) -> Callable[Concatenate[Any, P], R]:
    """Create a closure from `func`. This consumes the first `this` argument."""

    @functools.wraps(func)
    def wrapper(_this, *args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)

    return wrapper


def _add[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    closures[func.__name__] = func
    return func


@_add
@closure
def boolean(value: object) -> bool:
    """Get a boolean for `value`."""
    return bool(value)


@_add
@closure
def format_string(string: str, *args: Any) -> str:
    """Format `string` with `args`."""
    return string.format(*args)


@_add
@closure
def if_else[T](condition: object, first: T, second: T) -> T:
    """Return `first` or `second` depending on `condition`."""
    return first if condition else second


@_add
@closure
def shortcut(default: str, macos: str | None = None) -> Gtk.ShortcutTrigger | None:
    """Get the correct shortcut for the user's platform."""
    return Gtk.ShortcutTrigger.parse_string(
        (macos or default.replace("<Control>", "<Meta>"))
        if sys.platform.startswith("darwin")
        else default
    )
