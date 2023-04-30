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

    def __next__(self):
        raise NotImplementedError()


class Source(Iterable):
    """Source of games. Can be a program location on disk with a config file that points to game for example"""

    win = None
    schema_keys: dict

    name: str
    variant: str
    executable_format: str

    def __init__(self, win) -> None:
        super().__init__()
        self.win = win
        self.__init_schema_keys__()

    def __init_schema_keys__(self):
        """Initialize schema keys needed by the source if necessary"""
        raise NotImplementedError()

    @property
    def full_name(self):
        """Get the source's full name"""
        s = self.name
        if self.variant is not None:
            s += " (%s)" % self.variant
        return s

    @property
    def game_id_format(self):
        """Get the string format used to construct game IDs"""
        _format = self.name.lower()
        if self.variant is not None: 
            _format += "_" + self.variant.lower()
        _format += "_{game_id}_{game_internal_id}"
        return _format

    def __iter__(self):
        """Get the source's iterator, to use in for loops"""
        raise NotImplementedError()

    def __init_locations__(self):
        """Initialize locations needed by the source.
        Extended and called by **final** children."""
        raise NotImplementedError()