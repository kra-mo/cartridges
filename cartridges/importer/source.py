# source.py
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

import sys
from abc import abstractmethod
from collections.abc import Iterable
from typing import Any, Collection, Generator, Optional

from cartridges.game import Game
from cartridges.importer.location import Location, UnresolvableLocationError

# Type of the data returned by iterating on a Source
SourceIterationResult = Optional[Game | tuple[Game, tuple[Any]]]


class SourceIterable(Iterable):
    """Data producer for a source of games"""

    source: "Source"

    def __init__(self, source: "Source") -> None:
        self.source = source

    @abstractmethod
    def __iter__(self) -> Generator[SourceIterationResult, None, None]:
        """
        Method that returns a generator that produces games
        * Should be implemented as a generator method
        * May yield `None` when an iteration hasn't produced a game
        * In charge of handling per-game errors
        * Returns when exhausted
        """


class Source(Iterable):
    """Source of games. E.g an installed app with a config file that lists game directories"""

    source_id: str
    name: str
    variant: Optional[str] = None
    available_on: set[str] = set()
    iterable_class: type[SourceIterable]

    # NOTE: Locations must be set at __init__ time, not in the class definition.
    # They must not be shared between source instances.
    locations: Collection[Location]

    @property
    def full_name(self) -> str:
        """The source's full name"""
        full_name_ = self.name
        if self.variant:
            full_name_ += f" ({self.variant})"
        return full_name_

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.source_id + "_{game_id}"

    @property
    def is_available(self) -> bool:
        return sys.platform in self.available_on

    def make_executable(self, *args, **kwargs) -> str:
        """
        Create a game executable command.
        Should be implemented by child classes.
        """

    def __iter__(self) -> Generator[SourceIterationResult, None, None]:
        """
        Get an iterator for the source
        :raises UnresolvableLocationError: Not iterable
        if any of the mandatory locations are unresolvable
        """
        for location in self.locations:
            try:
                location.resolve()
            except UnresolvableLocationError as error:
                if not error.optional:
                    raise UnresolvableLocationError from error
        return iter(self.iterable_class(self))


class ExecutableFormatSource(Source):
    """Source class that uses a simple executable format to start games"""

    @property
    @abstractmethod
    def executable_format(self) -> str:
        """The executable format used to construct game executables"""

    def make_executable(self, *args, **kwargs) -> str:
        """Use the executable format to"""
        return self.executable_format.format(*args, **kwargs)


# pylint: disable=abstract-method
class URLExecutableSource(ExecutableFormatSource):
    """Source class that use custom URLs to start games"""

    url_format: str

    @property
    def executable_format(self) -> str:
        match sys.platform:
            case "win32":
                return "start " + self.url_format
            case "linux":
                return "xdg-open " + self.url_format
            case other:
                raise NotImplementedError(
                    f"No URL handler command available for {other}"
                )
