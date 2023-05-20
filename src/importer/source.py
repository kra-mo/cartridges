from abc import abstractmethod
from collections.abc import Iterable, Iterator, Sized

from src.game import Game
from src.window import CartridgesWindow


class SourceIterator(Iterator, Sized):
    """Data producer for a source of games"""

    source: "Source" = None

    def __init__(self, source: "Source") -> None:
        super().__init__()
        self.source = source

    def __iter__(self) -> "SourceIterator":
        return self

    @abstractmethod
    def __len__(self) -> int:
        """Get a rough estimate of the number of games produced by the source"""

    @abstractmethod
    def __next__(self) -> "Game" | None:
        """Get the next generated game from the source.
        Raises StopIteration when exhausted.
        May raise any other exception signifying an error on this specific game.
        May return None when a game has been skipped without an error."""


class Source(Iterable):
    """Source of games. E.g an installed app with a config file that lists game directories"""

    win: "CartridgesWindow" = None
    name: str
    variant: str

    def __init__(self, win) -> None:
        super().__init__()
        self.win = win

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
        format_ = self.name.lower()
        if self.variant is not None:
            format_ += f"_{self.variant.lower()}"
        format_ += "_{game_id}"
        return format_

    @property
    @abstractmethod
    def executable_format(self) -> str:
        """The executable format used to construct game executables"""

    @property
    @abstractmethod
    def is_installed(self) -> bool:
        """Whether the source is detected as installed"""

    @abstractmethod
    def __iter__(self) -> SourceIterator:
        """Get the source's iterator, to use in for loops"""
