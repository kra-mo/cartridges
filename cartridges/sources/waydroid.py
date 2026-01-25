# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

import itertools
from collections.abc import Generator
from gettext import gettext as _

from gi.repository import Gdk, GLib, Graphene, Gtk

from cartridges.cover import HEIGHT, WIDTH
from cartridges.games import Game

from . import DATA

_BLACKLIST = frozenset((
    "com.android.calculator2",
    "com.android.deskclock",
    "com.android.documentsui",
    "com.android.gallery3d",
    "com.android.settings",
    "com.android.vending",
    "com.google.android.apps.messaging",
    "com.google.android.apps.restore",
    "com.google.android.apps.safetyhub",
    "com.google.android.contacts",
    "com.google.android.googlequicksearchbox",
    "org.lineageos.aperture",
    "org.lineageos.eleven",
    "org.lineageos.etar",
    "org.lineageos.jelly",
    "org.lineageos.recorder",
))

ID, NAME = "waydroid", _("Waydroid")

_ICON_SIZE = 128


def get_games() -> Generator[Game]:
    """Installed games from Waydroid."""
    for path in itertools.chain((DATA / "applications").glob("waydroid*.desktop")):
        file = GLib.KeyFile()
        file.load_from_file(str(path), GLib.KeyFileFlags.NONE)

        executable = file.get_string("Desktop Entry", "Exec")
        if (apk_id := executable.replace("waydroid app launch ", "")) in _BLACKLIST:
            continue

        yield Game(
            executable=executable,
            game_id=apk_id,
            source=ID,
            name=file.get_string("Desktop Entry", "Name"),
            cover=_get_cover(apk_id),
        )


def _get_cover(apk_id: str) -> Gdk.Paintable | None:
    cover_path = str(DATA / "waydroid" / "data" / "icons" / apk_id)
    try:
        cover = Gdk.Texture.new_from_filename(str(cover_path + ".png"))
    except GLib.Error:
        return None

    snapshot = Gtk.Snapshot()
    snapshot.translate(
        Graphene.Point().init(
            (WIDTH - _ICON_SIZE) / 2,
            (HEIGHT - _ICON_SIZE) / 2,
        )
    )

    snapshot.append_texture(cover, Graphene.Rect().init(0, 0, _ICON_SIZE, _ICON_SIZE))

    return snapshot.to_paintable(Graphene.Size().init(WIDTH, HEIGHT))
