# decorators.py
#
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

from pathlib import Path
from os import PathLike
from functools import wraps

from src import shared


def replaced_by_path(override: PathLike):  # Decorator builder
    """Replace the method's returned path with the override
    if the override exists on disk"""

    def decorator(original_function):  # Built decorator (closure)
        @wraps(original_function)
        def wrapper(*args, **kwargs):  # func's override
            path = Path(override).expanduser()
            if path.exists():
                return path
            return original_function(*args, **kwargs)

        return wrapper

    return decorator


def replaced_by_schema_key(original_method):  # Built decorator (closure)
    """
    Replace the original method's value by the path pointed at in the schema
    by the class' location key (if that override exists)
    """

    @wraps(original_method)
    def wrapper(*args, **kwargs):  # func's override
        source = args[0]
        override = shared.schema.get_string(source.location_key)
        return replaced_by_path(override)(original_method)(*args, **kwargs)

    return wrapper
