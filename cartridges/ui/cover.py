# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from gi.repository import Adw, Gdk, GObject, Gtk

from cartridges.config import PREFIX


@Gtk.Template.from_resource(f"{PREFIX}/cover.ui")
class Cover(Adw.Bin):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    paintable = GObject.Property(type=Gdk.Paintable)
    width = GObject.Property(type=int, default=200)
    height = GObject.Property(type=int, default=300)

    @Gtk.Template.Callback()
    def _if_else[T](self, _obj, condition: object, first: T, second: T) -> T:
        return first if condition else second

    @Gtk.Template.Callback()
    def _concat(self, _obj, *strings: str) -> str:
        return "".join(strings)
