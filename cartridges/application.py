# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileCopyrightText: Copyright 2025 Zoey Ahmed
# SPDX-FileCopyrightText: Copyright 2025 kramo

from collections.abc import Generator, Iterable
from gettext import gettext as _
from typing import override

from gi.repository import Adw

from cartridges import SETTINGS, games
from cartridges.games import Collection, Game
from cartridges.sources import Source, steam

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
        new = self.import_games(steam, skip_ids={g.game_id for g in saved})
        games.model.splice(0, 0, (*saved, *new))

        games.collections.splice(0, 0, tuple(self.get_collections()))
        games.save_collections()

    @staticmethod
    def import_games(*sources: Source, skip_ids: Iterable[str]) -> Generator[Game]:
        """Import games from `sources`, skipping ones in `skip_ids`."""
        for source in sources:
            try:
                yield from source.get_games(skip_ids=skip_ids)
            except FileNotFoundError:
                continue

    @staticmethod
    def get_collections() -> Generator[Collection]:
        """Get collections from GSettings."""
        for collection_ in SETTINGS.get_value("collections").unpack():
            if collection_.get("removed"):
                continue

            collection = Collection()

            for prop, value in collection_.items():
                try:
                    collection.set_property(prop, value)
                except TypeError:
                    continue

            yield collection

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
