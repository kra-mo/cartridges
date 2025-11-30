# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 kramo

from gi.repository import Adw, Gdk, GObject, Gtk

from cartridges.config import PREFIX


@Gtk.Template.from_resource(f"{PREFIX}/cover.ui")
class Cover(Adw.Bin):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    paintable = GObject.Property(type=Gdk.Paintable)
