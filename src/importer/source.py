from abc import abstractmethod
from collections.abc import Iterable, Iterator
from enum import IntEnum, auto


class SourceIterator(Iterator):
    """Data producer for a source of games"""

    class States(IntEnum):
        DEFAULT = auto()
        READY = auto()
    
    state = States.DEFAULT
    source = None

    def __init__(self, source) -> None:
        super().__init__()
        self.source = source

    def __iter__(self):
        return self

    @abstractmethod
    def __next__(self):
        pass


class Source(Iterable):
    """Source of games. E.g an installed app with a config file that lists game directories"""

    win = None # TODO maybe not depend on that ?

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
            s += " (%s)" % self.variant
        return s

    @property
    def game_id_format(self):
        """The string format used to construct game IDs"""
        _format = self.name.lower()
        if self.variant is not None: 
            _format += "_" + self.variant.lower()
        _format += "_{game_id}_{game_internal_id}"
        return _format

    @property
    @abstractmethod
    def executable_format(self):
        """The executable format used to construct game executables"""
        pass

    @abstractmethod
    def __iter__(self):
        """Get the source's iterator, to use in for loops"""
        pass