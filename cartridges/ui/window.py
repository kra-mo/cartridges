from typing import Any

from gi.repository import Adw, Gtk

from cartridges.config import PREFIX, PROFILE


@Gtk.Template.from_resource(f"{PREFIX}/window.ui")
class Window(Adw.ApplicationWindow):
    """The main window."""

    __gtype_name__ = __qualname__

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        if PROFILE == "development":
            self.add_css_class("devel")
