# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025, 2026 kramo

from gi.repository import Adw, Gdk, GObject, Gtk

from cartridges import cover
from cartridges.config import PREFIX

from . import closures

COVER_ASPECT_RATIO = cover.WIDTH / cover.HEIGHT


@Gtk.Template(resource_path=f"{PREFIX}/cover.ui")
class Cover(Adw.Bin):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    paintable = GObject.Property(type=Gdk.Paintable)
    width = GObject.Property(type=int, default=cover.WIDTH)
    height = GObject.Property(type=int, default=cover.HEIGHT)

    format_string = closures.format_string
    if_else = closures.if_else

    @Gtk.Template.Callback()
    def _content_fit(self, _obj, paintable: Gdk.Paintable | None) -> Gtk.ContentFit:
        return (
            Gtk.ContentFit.COVER
            if paintable
            and COVER_ASPECT_RATIO - 0.1
            < paintable.get_intrinsic_aspect_ratio()
            < COVER_ASPECT_RATIO + 0.1
            else Gtk.ContentFit.CONTAIN
        )
