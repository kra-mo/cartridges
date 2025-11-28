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

from gi.repository import Gio

from .config import LOCALEDIR, PKGDATADIR

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
