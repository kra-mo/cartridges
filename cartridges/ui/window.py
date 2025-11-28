# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed

from typing import Any

from gi.repository import Adw, Gio, GObject, Gtk

from cartridges import games
from cartridges.config import PREFIX, PROFILE


@Gtk.Template.from_resource(f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    @GObject.Property(type=Gio.ListStore)
    def games(self) -> Gio.ListStore:
        """Model of the user's games."""
        return games.model

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        if PROFILE == "development":
            self.add_css_class("devel")
