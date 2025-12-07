# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 Jamie Gravendeel

import gettext
import locale
import signal
import sys
from pathlib import Path

import gi

gi.require_versions({
    "Gtk": "4.0",
    "Adw": "1",
})

if sys.platform.startswith("linux"):
    gi.require_version("Manette", "0.2")


from gi.repository import Gio, GLib

from .config import APP_ID, LOCALEDIR, PKGDATADIR

DATA_DIR = Path(GLib.get_user_data_dir(), "cartridges")
SETTINGS = Gio.Settings.new(APP_ID)
STATE_SETTINGS = Gio.Settings.new(f"{APP_ID}.State")

_RESOURCES = ("data", "icons", "ui")

signal.signal(signal.SIGINT, signal.SIG_DFL)

if sys.platform.startswith("linux"):
    locale.bindtextdomain("cartridges", LOCALEDIR)
    locale.textdomain("cartridges")

gettext.bindtextdomain("cartridges", LOCALEDIR)
gettext.textdomain("cartridges")

for name in _RESOURCES:
    path = Path(PKGDATADIR, name).with_suffix(".gresource")
    resource = Gio.Resource.load(str(path))
    Gio.resources_register(resource)
