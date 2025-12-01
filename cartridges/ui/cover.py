# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from gi.repository import Adw, Gdk, GObject, Gtk

from cartridges.config import APP_ID, PREFIX


@Gtk.Template.from_resource(f"{PREFIX}/cover.ui")
class Cover(Adw.Bin):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    picture = GObject.Property(lambda self: self._picture, type=Gtk.Picture)
    paintable = GObject.Property(type=Gdk.Paintable)
    app_icon_name = GObject.Property(type=str, default=f"{APP_ID}-symbolic")

    _picture = Gtk.Template.Child()

    @Gtk.Template.Callback()
    def _get_stack_child(self, _obj, paintable: Gdk.Paintable | None) -> str:
        return "cover" if paintable else "icon"
