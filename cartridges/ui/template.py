# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

import functools
import re
import typing
from collections.abc import Callable
from typing import Any

from gi.repository import GObject, Gtk

from cartridges.config import PREFIX

from .closures import closures

type Child[T: GObject.Object] = T


def set_template[T: type[Gtk.Widget]](cls: T) -> T:
    """Create a GTK template.

    The resource path is derived from the ClassName converted to kebab-case.

    Children are defined with the Child type alias.
    """
    cls.set_template_from_resource(f"{PREFIX}/{_pascal_to_kebab(cls.__name__)}.ui")
    cls.set_template_scope(_BuilderScope())
    # PyGObject automatically runs __dontuse_ginstance_init__:
    # https://gitlab.gnome.org/GNOME/pygobject/-/blob/4d239e0c36301465a863c6e47e49c2b526799ab2/gi/pygobject-object.c#L760
    cls.__dontuse_ginstance_init__ = _init_template  # pyright: ignore[reportAttributeAccessIssue]
    for child in _get_children(cls):
        cls.bind_template_child_full(child, False, 0)
    return cls


class _BuilderScope(GObject.Object, Gtk.BuilderScope):
    def do_create_closure(
        self, builder: Gtk.Builder, func_name: str, _flags, _obj
    ) -> Callable[..., Any]:
        """Create a closure with the given arguments.

        This first tries looking up `func_name` in the template class,
        and falls back to looking it up in a list of closures.
        """
        template = builder.props.current_object
        if callback := getattr(template, func_name, closures.get(func_name)):
            return callback

        msg = f"'{func_name}' is not an available callback"
        raise RuntimeError(msg)


def _pascal_to_kebab(string: str) -> str:
    return re.sub("(?<=[a-z])(?=[A-Z])", "-", string).lower()


def _init_template(self: Gtk.Widget):
    self.init_template()
    for child in _get_children(type(self)):
        setattr(self, child, self.get_template_child(type(self), child))


@functools.cache
def _get_children(cls: type[Gtk.Widget]) -> tuple[str, ...]:
    return tuple(
        name
        for name, obj in typing.get_type_hints(cls).items()
        if typing.get_origin(obj) is Child
    )
