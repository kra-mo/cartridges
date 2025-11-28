from gettext import gettext as _
from typing import override

from gi.repository import Adw

from .config import APP_ID, PREFIX
from .ui.window import Window


class Application(Adw.Application):
    """The main application."""

    def __init__(self) -> None:
        super().__init__(application_id=APP_ID)

        self.add_action_entries((
            ("quit", lambda *_: self.quit()),
            ("about", lambda *_: self._present_about_dialog()),
        ))
        self.set_accels_for_action("app.quit", ("<Control>q",))

    @override
    def do_activate(self) -> None:
        window = self.props.active_window or Window(application=self)
        window.present()

    def _present_about_dialog(self) -> None:
        dialog = Adw.AboutDialog.new_from_appdata(f"{PREFIX}/{APP_ID}.metainfo.xml")
        # Translators: Replace "translator-credits" with your name/username,
        # and optionally a URL or an email in <me@example.org> format.
        dialog.props.translator_credits = _("translator-credits")
        dialog.present(self.props.active_window)
