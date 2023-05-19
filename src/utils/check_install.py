# check_install.py
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

from pathlib import Path


# TODO delegate to the sources
def check_install(check, locations, setting=None, subdirs=(Path(),)):
    for location in locations:
        for subdir in (Path(),) + subdirs:
            if (location / subdir / check).is_file() or (
                location / subdir / check
            ).exists():
                if setting:
                    setting[0].set_string(setting[1], str(location / subdir))

                return location / subdir
