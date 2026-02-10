# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025-2026 kramo

from gettext import gettext as _
from typing import override

from gi.repository import Adw

from . import sources
from .config import APP_ID, PREFIX
from .ui import PRIMARY_KEY
from .ui.window import Window


class Application(Adw.Application):
    """The main application."""

    __gtype_name__ = __qualname__

    @override
    def do_startup(self):
        Adw.Application.do_startup(self)
        self.props.style_manager.props.color_scheme = Adw.ColorScheme.PREFER_DARK

        self.add_action_entries((
            ("about", lambda *_: self._present_about_dialog()),
            ("quit", lambda *_: self.quit()),
        ))
        self.set_accels_for_action("app.quit", (f"{PRIMARY_KEY}q",))

        sources.load()

    @override
    def do_activate(self):
        window = self.props.active_window or Window(application=self)
        window.present()

    def _present_about_dialog(self):
        about = Adw.AboutDialog(appdata_resource_path=f"{PREFIX}/{APP_ID}.metainfo.xml")  # pyright: ignore[reportCallIssue]
        # Translators: Replace "translator-credits" with your name/username,
        # and optionally a URL or an email in <user@example.org> format.
        about.props.translator_credits = _("translator-credits")
        about.present(self.props.active_window)
