# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo

from collections.abc import Generator, Iterable
from gettext import gettext as _
from typing import override

from gi.repository import Adw

from cartridges import games
from cartridges.games import Game
from cartridges.sources import Source, SteamSource

from .config import APP_ID, PREFIX
from .ui.window import Window


class Application(Adw.Application):
    """The main application."""

    def __init__(self):
        super().__init__(application_id=APP_ID)

        self.add_action_entries((
            ("quit", lambda *_: self.quit()),
            ("about", lambda *_: self._present_about_dialog()),
        ))
        self.set_accels_for_action("app.quit", ("<Control>q",))

        saved = tuple(games.load())
        new = self.import_games(SteamSource(), skip_ids={g.game_id for g in saved})
        games.model.splice(0, 0, (*saved, *new))

    @staticmethod
    def import_games(*sources: Source, skip_ids: Iterable[str]) -> Generator[Game]:
        """Import games from `sources`, skipping ones in `skip_ids`."""
        for source in sources:
            try:
                new = source.get_games(skip_ids=skip_ids)
            except FileNotFoundError:
                continue

            yield from new

    @override
    def do_startup(self):
        Adw.Application.do_startup(self)
        Adw.StyleManager.get_default().props.color_scheme = Adw.ColorScheme.PREFER_DARK

    @override
    def do_activate(self):
        window = self.props.active_window or Window(application=self)
        window.present()

    def _present_about_dialog(self):
        dialog = Adw.AboutDialog.new_from_appdata(f"{PREFIX}/{APP_ID}.metainfo.xml")
        # Translators: Replace "translator-credits" with your name/username,
        # and optionally a URL or an email in <user@example.org> format.
        dialog.props.translator_credits = _("translator-credits")
        dialog.present(self.props.active_window)
