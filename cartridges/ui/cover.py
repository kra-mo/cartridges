# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025, 2026 kramo
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

from typing import cast, override

from gi.repository import Gdk, GObject, Gtk

from cartridges import cover

from . import template

COVER_ASPECT_RATIO = cover.WIDTH / cover.HEIGHT


@template.set_template
class Cover(Gtk.Widget):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    paintable = GObject.Property(type=Gdk.Paintable)

    def __init__(self):
        super().__init__()

        self.set_size_request(cover.WIDTH, cover.HEIGHT)

    @override
    def do_size_allocate(self, width: int, height: int, baseline: int):
        allocation = Gdk.Rectangle()
        allocation.width = self.props.width_request
        allocation.height = self.props.height_request
        allocation.x = (width - self.props.width_request) // 2
        child = cast(Gtk.Widget, self.get_first_child())
        child.size_allocate(allocation, baseline)

    def _content_fit(self, _obj, paintable: Gdk.Paintable | None) -> Gtk.ContentFit:
        return (
            Gtk.ContentFit.COVER
            if paintable
            and COVER_ASPECT_RATIO - 0.1
            < paintable.get_intrinsic_aspect_ratio()
            < COVER_ASPECT_RATIO + 0.1
            else Gtk.ContentFit.CONTAIN
        )
