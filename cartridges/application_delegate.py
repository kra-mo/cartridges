# application_delegate.py
#
# Copyright 2024 kramo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""A set of methods that manage your app’s life cycle and its interaction
with common system services."""

from typing import Any

from AppKit import NSApp, NSApplication, NSMenu, NSMenuItem  # type: ignore
from Foundation import NSObject  # type: ignore
from gi.repository import Gio  # type: ignore

from cartridges import shared


class ApplicationDelegate(NSObject):  # type: ignore
    """A set of methods that manage your app’s life cycle and its interaction
    with common system services."""

    def applicationDidFinishLaunching_(self, *_args: Any) -> None:
        main_menu = NSApp.mainMenu()

        add_game_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Add Game", "add:", "n"
        )

        import_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Import", "import:", "i"
        )

        file_menu = NSMenu.alloc().init()
        file_menu.addItem_(add_game_menu_item)
        file_menu.addItem_(import_menu_item)

        file_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "File", None, ""
        )
        file_menu_item.setSubmenu_(file_menu)
        main_menu.addItem_(file_menu_item)

        show_hidden_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Show Hidden", "hidden:", "h"
        )

        windows_menu = NSMenu.alloc().init()

        view_menu = NSMenu.alloc().init()
        view_menu.addItem_(show_hidden_menu_item)

        view_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "View", None, ""
        )
        view_menu_item.setSubmenu_(view_menu)
        main_menu.addItem_(view_menu_item)

        windows_menu = NSMenu.alloc().init()

        windows_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Window", None, ""
        )
        windows_menu_item.setSubmenu_(windows_menu)
        main_menu.addItem_(windows_menu_item)

        NSApp.setWindowsMenu_(windows_menu)

        keyboard_shortcuts_menu_item = (
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Keyboard Shortcuts", "shortcuts:", "?"
            )
        )

        help_menu = NSMenu.alloc().init()
        help_menu.addItem_(keyboard_shortcuts_menu_item)

        help_menu_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Help", None, ""
        )
        help_menu_item.setSubmenu_(help_menu)
        main_menu.addItem_(help_menu_item)

        NSApp.setHelpMenu_(help_menu)

    def add_(self, *_args: Any) -> None:
        if (not shared.win) or (not (app := shared.win.get_application())):
            return

        app.lookup_action("add_game").activate()

    def import_(self, *_args: Any) -> None:
        if (not shared.win) or (not (app := shared.win.get_application())):
            return

        app.lookup_action("import").activate()

    def hidden_(self, *_args: Any) -> None:
        if not shared.win:
            return

        shared.win.lookup_action("show_hidden").activate()

    def shortcuts_(self, *_args: Any) -> None:
        if (not shared.win) or (not (overlay := shared.win.get_help_overlay())):
            return

        overlay.present()
