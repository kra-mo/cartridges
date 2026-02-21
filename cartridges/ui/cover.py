# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025, 2026 kramo

from gi.repository import Adw, Gdk, GObject

from cartridges.games import COVER_HEIGHT, COVER_WIDTH

from .template import template


@template
class Cover(Adw.Bin):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    paintable = GObject.Property(type=Gdk.Paintable)
    width = GObject.Property(type=int, default=COVER_WIDTH)
    height = GObject.Property(type=int, default=COVER_HEIGHT)
