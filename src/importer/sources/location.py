from pathlib import Path
from typing import Callable, Mapping, Iterable
from os import PathLike

PathSegment = str | PathLike | Path
PathSegments = Iterable[PathSegment]
Candidate = PathSegments | Callable[[], PathSegments]


class UnresolvableLocationError(Exception):
    pass


class Location:
    """
    Class representing a filesystem location

    * A location may have multiple candidate roots
    * From its root, multiple subpaths are named and should exist
    """

    candidates: Iterable[Candidate]
    paths: Mapping[str, tuple[bool, PathSegments]]
    root: Path = None

    def __init__(
        self,
        candidates: Iterable[Candidate],
        paths: Mapping[str, tuple[bool, PathSegments]],
    ) -> None:
        super().__init__()
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
        for candidate in self.candidates:
            if callable(candidate):
                candidate = candidate()
            candidate = Path(candidate).expanduser()
            if self.check_candidate(candidate):
                self.root = candidate
                return
        raise UnresolvableLocationError()

    def __getitem__(self, key: str):
        """Get the computed path from its key for the location"""
        self.resolve()
        return self.root / self.paths[key][1]
