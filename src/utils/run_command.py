# run_command.py
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

import os
import shlex
import subprocess
import sys

from gi.repository import Gio


def run_command(executable):
    use_shell = False
    if not use_shell:
        # The host environment is automatically passed through by Popen.
        subprocess.Popen(
            ["flatpak-spawn", "--host", *executable]  # Flatpak
            if os.getenv("FLATPAK_ID") == "hu.kramo.Cartridges"
            else executable  # Windows
            if os.name == "nt"
            else executable,  # Linux/Others
            shell=False,  # If true, the extra arguments would incorrectly be given to the shell instead.
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
    else:
        # When launching as a shell, we must pass 1 string with the exact command
        # line exactly as we would type it in a shell (with escaped arguments).
        subprocess.Popen(
            shlex.join(
                ["flatpak-spawn", "--host", *executable]  # Flatpak
                if os.getenv("FLATPAK_ID") == "hu.kramo.Cartridges"
                else executable  # Windows
                if os.name == "nt"
                else executable  # Linux/Others
            ),
            shell=True,
            start_new_session=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )
    if Gio.Settings.new("hu.kramo.Cartridges").get_boolean("exit-after-launch"):
        sys.exit()
