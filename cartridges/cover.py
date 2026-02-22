# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2026 kramo

from collections import defaultdict
from io import BytesIO
from os import PathLike
from urllib.request import urlopen

import PIL
from gi.repository import Gdk, GLib, GObject, Graphene, Gtk
from PIL import Image

from . import DATA_DIR

COVERS_DIR = DATA_DIR / "covers"

WIDTH = 200
HEIGHT = 300
ICON_SIZE = 128


class _PILPaintable(GObject.Object, Gdk.Paintable):
    def __init__(self, im: Image.Image):
        super().__init__()

        self.im = im
        self.needs_update = True
        self.flags = Gdk.PaintableFlags.STATIC_SIZE
        self.frames = defaultdict(
            lambda: Gdk.MemoryTexture.new(
                self.im.width,
                self.im.height,
                Gdk.MemoryFormat.R8G8B8A8,
                GLib.Bytes.new(self.im.convert("RGBA").tobytes()),
                self.im.width * 4,
            )
        )

        if not getattr(self.im, "is_animated", False):
            self.needs_update = False
            self.flags |= Gdk.PaintableFlags.STATIC_CONTENTS

    def do_get_current_image(self) -> Gdk.Paintable:
        return self.frames[self.im.tell()]

    def do_get_intrinsic_height(self) -> int:
        return self.im.height

    def do_get_intrinsic_width(self) -> int:
        return self.im.width

    def do_get_flags(self) -> Gdk.PaintableFlags:
        return self.flags

    def do_snapshot(self, snapshot: Gdk.Snapshot, width: int, height: int):
        self.do_get_current_image().snapshot(snapshot, width, height)
        if self.needs_update:
            self.needs_update = False
            GLib.timeout_add(self.im.info.get("duration", 100), self.update_frame)

    def update_frame(self):
        try:
            self.im.seek(self.im.tell() + 1)
        except EOFError:
            self.im.seek(0)

        self.needs_update = True
        self.invalidate_contents()


def at_path(path: PathLike[str] | str) -> Gdk.Paintable | None:
    """Load the cover at `path`."""
    try:
        return _PILPaintable(Image.open(path))
    except (FileNotFoundError, PIL.UnidentifiedImageError):
        return None


def at_url(url: str) -> Gdk.Paintable | None:
    """Load the cover at the remote `url`."""
    with urlopen(url) as response:  # TODO: Rate limiting?
        contents = response.read()

    try:
        return _PILPaintable(Image.open(BytesIO(contents)))
    except PIL.UnidentifiedImageError:
        return None


def from_icon(icon: Gdk.Paintable) -> Gdk.Paintable | None:
    """Pad `icon` to be appropriate for a cover."""
    snapshot = Gtk.Snapshot()
    snapshot.translate(
        Graphene.Point().init(
            (WIDTH - ICON_SIZE) / 2,
            (HEIGHT - ICON_SIZE) / 2,
        )
    )
    icon.snapshot(snapshot, ICON_SIZE, ICON_SIZE)
    return snapshot.to_paintable(Graphene.Size().init(WIDTH, HEIGHT))
