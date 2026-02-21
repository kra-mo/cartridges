# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025, 2026 kramo
# SPDX-FileCopyrightText: Copyright 2026 Jamie Gravendeel

from typing import NamedTuple, cast, override

from gi.repository import Adw, Gdk, GObject, Gtk

from cartridges import cover
from cartridges.config import PREFIX

from . import closures

COVER_ASPECT_RATIO = cover.WIDTH / cover.HEIGHT


class _Measurement(NamedTuple):
    minimum: int
    natural: int
    minimum_baseline: int
    natural_baseline: int


class CoverLayoutManager(Gtk.LayoutManager):
    """A layout manager with a fixed size."""

    __gtype_name__ = __qualname__

    width = GObject.Property(type=int)
    height = GObject.Property(type=int)

    @override
    def do_get_request_mode(self, widget: Gtk.Widget) -> Gtk.SizeRequestMode:
        return Gtk.SizeRequestMode.CONSTANT_SIZE

    @override
    def do_measure(
        self,
        widget: Gtk.Widget,
        orientation: Gtk.Orientation,
        for_size: int,
    ) -> _Measurement:
        size = self.width if orientation is Gtk.Orientation.HORIZONTAL else self.height
        return _Measurement(size, size, -1, -1)

    @override
    def do_allocate(self, widget: Gtk.Widget, width: int, height: int, baseline: int):
        allocation = Gdk.Rectangle()
        allocation.width = self.width
        allocation.height = self.height
        allocation.x = (width - self.width) / 2
        allocation.y = (height - self.height) / 2
        child = cast(Gtk.Widget, widget.get_first_child())
        child.size_allocate(allocation, baseline)


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
