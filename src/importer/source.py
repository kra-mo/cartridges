from abc import abstractmethod
from collections.abc import Iterable, Iterator, Sized


class SourceIterator(Iterator, Sized):
    """Data producer for a source of games"""

    source = None

    def __init__(self, source) -> None:
        super().__init__()
        self.source = source

    def __iter__(self):
        return self

    @abstractmethod
    def __len__(self):
        pass

    @abstractmethod
    def __next__(self):
        pass


class Source(Iterable):
    """Source of games. E.g an installed app with a config file that lists game directories"""

    win = None  # TODO maybe not depend on that ?

    name: str
    variant: str

    def __init__(self, win) -> None:
        super().__init__()
        self.win = win

    @property
    def full_name(self):
        """The source's full name"""
        full_name_ = self.name
        if self.variant is not None:
            full_name_ += f" ({self.variant})"
        return full_name_

    @property
    def id(self):  # pylint: disable=invalid-name
        """The source's identifier"""
        id_ = self.name.lower()
        if self.variant is not None:
            id_ += f"_{self.variant.lower()}"
        return id_

    @property
    def game_id_format(self):
        """The string format used to construct game IDs"""
        format_ = self.name.lower()
        if self.variant is not None:
            format_ += f"_{self.variant.lower()}"
        format_ += "_{game_id}"
        return format_

    @property
    @abstractmethod
    def executable_format(self):
        """The executable format used to construct game executables"""

    @property
    @abstractmethod
    def is_installed(self):
        """Whether the source is detected as installed"""

    @abstractmethod
    def __iter__(self):
        """Get the source's iterator, to use in for loops"""
