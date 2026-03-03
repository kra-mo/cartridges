# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

# ruff: noqa: D103

import functools
import sys
from collections.abc import Callable
from typing import Concatenate

from gi.repository import Gtk


def add[T: type[Gtk.Widget]](*closures: Callable[..., object]) -> Callable[[T], T]:
    """Add `closures` to a widget."""

    def decorator(cls: T) -> T:
        for closure in closures:
            name = closure.__name__.rstrip("_")
            cb = Gtk.Template.Callback(name)(staticmethod(closure))
            setattr(cls, f"_closure_{name}", cb)
        return cls

    return decorator


def _closure[**P, R](func: Callable[P, R]) -> Callable[Concatenate[object, P], R]:
    @functools.wraps(func)
    def wrapper(_this, *args: P.args, **kwargs: P.kwargs) -> R:
        return func(*args, **kwargs)

    return wrapper


@_closure
def all_(*values: object) -> bool:
    return all(values)


@_closure
def bool_(value: object) -> bool:
    return bool(value)


@_closure
def format_(string: str, *args: object) -> str:
    return string.format(*args)


@_closure
def if_[T](condition: object, first: T, second: T) -> T:
    return first if condition else second


@_closure
def not_(value: object) -> bool:
    return not value


@_closure
def shortcut(default: str, macos: str | None = None) -> Gtk.ShortcutTrigger | None:
    return Gtk.ShortcutTrigger.parse_string(
        (macos or default.replace("<Control>", "<Meta>"))
        if sys.platform.startswith("darwin")
        else default
    )
