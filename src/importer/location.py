from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from os import PathLike


@dataclass
class Location():
    """Abstraction for a location that has multiple candidate paths"""

    candidates: list[PathLike] = None
    
    def __init__(self, *candidates):
        self.candidates = list()
        self.candidates.extend(candidates)
        return self

    def add(self, canddiate):
        """Add a candidate (last evaluated)"""
        self.candidates.append(canddiate)
        return self
    
    def add_override(self, candidate):
        """Add a canddiate (first evaluated)"""
        self.candidates.insert(0, candidate)
        return self

    @cached_property
    def path(self):
        """Chosen path depending on availability on the disk."""
        for candidate in self.candidates:
            p = Path(candidate).expanduser()
            if p.exists: 
                return p
        return None