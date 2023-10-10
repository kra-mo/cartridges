# sqlite.py
#
# Copyright 2022-2023 kramo
# Copyright 2023 Geoffrey Coulaud
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

from glob import escape
from pathlib import Path
from shutil import copyfile

from gi.repository import GLib


def copy_db(original_path: Path) -> Path:
    """
    Copy a sqlite database to a cache dir and return its new path.
    The caller in in charge of deleting the returned path's parent dir.
    """
    tmp = Path(GLib.Dir.make_tmp())
    for file in original_path.parent.glob(f"{escape(original_path.name)}*"):
        copy = tmp / file.name
        copyfile(str(file), str(copy))
    return tmp / original_path.name
