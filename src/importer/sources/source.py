import sys
from abc import abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Generator, Any

from src import shared
from src.game import Game

# Type of the data returned by iterating on a Source
SourceIterationResult = None | Game | tuple[Game, tuple[Any]]


class SourceIterator(Iterator):
    """Data producer for a source of games"""

    source: "Source" = None
    generator: Generator = None

    def __init__(self, source: "Source") -> None:
        super().__init__()
        self.source = source
        self.generator = self.generator_builder()

    def __iter__(self) -> "SourceIterator":
        return self

    def __next__(self) -> SourceIterationResult:
        return next(self.generator)

    @abstractmethod
    def generator_builder(self) -> Generator[SourceIterationResult, None, None]:
        """
        Method that returns a generator that produces games
        * Should be implemented as a generator method
        * May yield `None` when an iteration hasn't produced a game
        * In charge of handling per-game errors
        * Returns when exhausted
        """


class Source(Iterable):
    """Source of games. E.g an installed app with a config file that lists game directories"""

    name: str
    iterator_class: type[SourceIterator]
    variant: str = None
    available_on: set[str] = set()

    @property
    def full_name(self) -> str:
        """The source's full name"""
        full_name_ = self.name
        if self.variant is not None:
            full_name_ += f" ({self.variant})"
        return full_name_

    @property
    def id(self) -> str:  # pylint: disable=invalid-name
        """The source's identifier"""
        id_ = self.name.lower()
        if self.variant is not None:
            id_ += f"_{self.variant.lower()}"
        return id_

    @property
    def game_id_format(self) -> str:
        """The string format used to construct game IDs"""
        return self.name.lower() + "_{game_id}"

    @property
    def is_installed(self):
        # pylint: disable=pointless-statement
        try:
            self.location
        except FileNotFoundError:
            return False
        return sys.platform in self.available_on

    @property
    def location_key(self) -> str:
        """
        The schema key pointing to the user-set location for the source.
        May be overriden by inherinting classes.
        """
        return f"{self.name.lower()}-location"

    def update_location_schema_key(self):
        """Update the schema value for this source's location if possible"""
        try:
            location = self.location
        except FileNotFoundError:
            return
        shared.schema.set_string(self.location_key, location)

    def __iter__(self) -> SourceIterator:
        """Get an iterator for the source"""
        return self.iterator_class(self)

    @property
    @abstractmethod
    def location(self) -> Path:
        """The source's location on disk"""

    @property
    @abstractmethod
    def executable_format(self) -> str:
        """The executable format used to construct game executables"""


# pylint: disable=abstract-method
class URLExecutableSource(Source):
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
