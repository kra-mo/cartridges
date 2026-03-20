# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025, 2026 kramo
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

from typing import cast, override

from gi.repository import Adw, Gdk, GObject, Gtk

from cartridges import cover
from cartridges.config import PREFIX

from . import closures

COVER_ASPECT_RATIO = cover.WIDTH / cover.HEIGHT


@Gtk.Template(resource_path=f"{PREFIX}/cover.ui")
@closures.add(closures.format_, closures.if_)
class Cover(Adw.Bin):
    """Displays a game's cover art."""

    __gtype_name__ = __qualname__

    paintable = GObject.Property(type=Gdk.Paintable)

    def __init__(self):
        super().__init__()

        self.set_size_request(cover.WIDTH, cover.HEIGHT)

    @Gtk.Template.Callback()
    @staticmethod
    def _content_fit(_this, paintable: Gdk.Paintable | None) -> Gtk.ContentFit:
        return (
            Gtk.ContentFit.COVER
            if paintable
            and COVER_ASPECT_RATIO - 0.1
            < paintable.get_intrinsic_aspect_ratio()
            < COVER_ASPECT_RATIO + 0.1
            else Gtk.ContentFit.CONTAIN
        )


class CoverLayoutManager(Gtk.LayoutManager):
    """A layout manager for `Cover` with an exact size."""

    __gtype_name__ = __qualname__

    @override
    def do_measure(
        self,
        widget: Gtk.Widget,
        orientation: Gtk.Orientation,
        for_size: int,
    ) -> tuple[int, int, int, int]:
        size = widget.get_size_request()[orientation]
        return size, size, -1, -1

    @override
    def do_allocate(self, widget: Gtk.Widget, width: int, height: int, baseline: int):
        allocation = Gdk.Rectangle()
        allocation.width = widget.props.width_request
        allocation.height = widget.props.height_request
        allocation.x = (width - widget.props.width_request) // 2
        cast(Gtk.Widget, widget.get_first_child()).size_allocate(allocation, baseline)
