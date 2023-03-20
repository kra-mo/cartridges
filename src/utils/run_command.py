# run_command.py
#
# Copyright 2022 kramo
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

import os
import subprocess
import sys

from gi.repository import Gio


def run_command(executable):
    subprocess.Popen(
        ["flatpak-spawn --host " + executable]
        if os.getenv("FLATPAK_ID") == "hu.kramo.Cartridges"
        else executable.split()
        if os.name == "nt"
        else [executable],
        shell=True,
        start_new_session=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    if Gio.Settings.new("hu.kramo.Cartridges").get_boolean("exit-after-launch"):
        sys.exit()
