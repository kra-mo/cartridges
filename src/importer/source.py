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
    name: str = "GenericSource"
    variant: str = None

    # Format to construct the executable command for a game.
    # Available field names depend on the implementation 
    executable_format: str

    def __init__(self, win) -> None:
        super().__init__()
        self.win = win

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