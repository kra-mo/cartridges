# create_dialog.py
#
# Copyright 2022-2023 kramo
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Optional

from gi.repository import Adw, Gtk


def create_dialog(
    win: Gtk.Window,
    heading: str,
    body: str,
    extra_option: Optional[str] = None,
    extra_label: Optional[str] = None,
) -> Adw.MessageDialog:
    dialog = Adw.MessageDialog.new(win, heading, body)
    dialog.add_response("dismiss", _("Dismiss"))

    if extra_option:
        dialog.add_response(extra_option, _(extra_label))

    dialog.present()
    return dialog
