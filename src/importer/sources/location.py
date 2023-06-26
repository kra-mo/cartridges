import logging
from pathlib import Path
from typing import Callable, Mapping, Iterable
from os import PathLike

from src import shared

PathSegment = str | PathLike | Path
PathSegments = Iterable[PathSegment]
Candidate = PathSegments | Callable[[], PathSegments]


class UnresolvableLocationError(Exception):
    pass


class Location:
    """
    Class representing a filesystem location

    * A location may have multiple candidate roots
    * The path in the schema is always favored
    * From the candidate root, multiple subpaths should exist for it to be valid
    * When resolved, the schema is updated with the picked chosen
    """

    schema_key: str
    candidates: Iterable[Candidate]
    paths: Mapping[str, tuple[bool, PathSegments]]
    root: Path = None

    def __init__(
        self,
        schema_key: str,
        candidates: Iterable[Candidate],
        paths: Mapping[str, tuple[bool, PathSegments]],
    ) -> None:
        super().__init__()
        self.schema_key = schema_key
        self.candidates = candidates
        self.paths = paths

    def check_candidate(self, candidate: Path) -> bool:
        """Check if a candidate root has the necessary files and directories"""
        for type_is_dir, subpath in self.paths.values():
            subpath = Path(candidate) / Path(subpath)
            if type_is_dir:
                if not subpath.is_dir():
                    return False
            else:
                if not subpath.is_file():
                    return False
        return True

    def resolve(self) -> None:
        """Choose a root path from the candidates for the location.
        If none fits, raise a UnresolvableLocationError"""

        if self.root is not None:
            return

        # Get the schema candidate
        schema_candidate = shared.schema.get_string(self.schema_key)

        # Find the first matching candidate
        for candidate in (schema_candidate, *self.candidates):
            candidate = Path(candidate).expanduser()
            if not self.check_candidate(candidate):
                continue
            self.root = candidate
            break
        else:
            # No good candidate found
            raise UnresolvableLocationError()

        # Update the schema with the found candidate
        value = str(candidate)
        shared.schema.set_string(self.schema_key, value)
        logging.debug("Resolved value for schema key %s: %s", self.schema_key, value)

    def __getitem__(self, key: str):
        """Get the computed path from its key for the location"""
        self.resolve()
        return self.root / self.paths[key][1]
