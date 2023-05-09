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
        s = self.name
        if self.variant is not None:
            s += f" ({self.variant})"
        return s

    @property
    def id(self):
        """The source's identifier"""
        s = self.name.lower()
        if self.variant is not None:
            s += f"_{self.variant.lower()}"
        return s

    @property
    def game_id_format(self):
        """The string format used to construct game IDs"""
        f = self.name.lower()
        if self.variant is not None:
            f += f"_{self.variant.lower()}"
        f += "_{game_id}"
        return f

    @property
    @abstractmethod
    def executable_format(self):
        """The executable format used to construct game executables"""
        pass

    @property
    @abstractmethod
    def is_installed(self):
        """Whether the source is detected as installed"""
        pass

    @abstractmethod
    def __iter__(self):
        """Get the source's iterator, to use in for loops"""
        pass
