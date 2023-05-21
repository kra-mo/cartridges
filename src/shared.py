# shared.py
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
from pathlib import Path

from gi.repository import Gdk, Gio

schema = Gio.Settings.new("hu.kramo.Cartridges")
state_schema = Gio.Settings.new("hu.kramo.Cartridges.State")

data_dir = (
    Path(os.getenv("XDG_DATA_HOME"))
    if "XDG_DATA_HOME" in os.environ
    else Path.home() / ".local" / "share"
)
config_dir = (
    Path(os.getenv("XDG_CONFIG_HOME"))
    if "XDG_CONFIG_HOME" in os.environ
    else Path.home() / ".config"
)
cache_dir = (
    Path(os.getenv("XDG_CACHE_HOME"))
    if "XDG_CACHE_HOME" in os.environ
    else Path.home() / ".cache"
)

games_dir = data_dir / "cartridges" / "games"
covers_dir = data_dir / "cartridges" / "covers"

scale_factor = max(
    monitor.get_scale_factor() for monitor in Gdk.Display.get_default().get_monitors()
)
image_size = (200 * scale_factor, 300 * scale_factor)

# pylint: disable=invalid-name
win = None
importer = None
