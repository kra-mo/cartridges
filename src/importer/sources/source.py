import sys
from abc import abstractmethod
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Optional, Generator

from src.game import Game


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

    def __next__(self) -> Optional[Game]:
        return next(self.generator)

    @abstractmethod
    def generator_builder(self) -> Generator[Optional[Game], None, None]:
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
    variant: str
    available_on: set[str]

    def __init__(self) -> None:
        super().__init__()
        self.available_on = set()

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
    @abstractmethod
    def location(self) -> Path:
        """The source's location on disk"""

    @property
    @abstractmethod
    def executable_format(self) -> str:
        """The executable format used to construct game executables"""

    @abstractmethod
    def __iter__(self) -> SourceIterator:
        """Get the source's iterator, to use in for loops"""


class WindowsSource(Source):
    """Mixin for sources available on Windows"""

    def __init__(self) -> None:
        super().__init__()
        self.available_on.add("win32")


class LinuxSource(Source):
    """Mixin for sources available on Linux"""

    def __init__(self) -> None:
        super().__init__()
        self.available_on.add("linux")
