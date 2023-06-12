import lzma
from io import StringIO
from logging import StreamHandler
from lzma import FORMAT_XZ, PRESET_DEFAULT
from os import PathLike
from pathlib import Path


class SessionFileHandler(StreamHandler):
    """
    A logging handler that writes to a new file on every app restart.
    The files are compressed and older sessions logs are kept up to a small limit.
    """

    backup_count: int
    filename: Path
    log_file: StringIO = None

    def create_dir(self) -> None:
        """Create the log dir if needed"""
        self.filename.parent.mkdir(exist_ok=True)

    def rotate_file(self, file: Path):
        """Rotate a file's number suffix and remove it if it's too old"""

        # Skip non interesting dir entries
        if not (file.is_file() and file.name.startswith(self.filename.name)):
            return

        # Compute the new number suffix
        suffixes = file.suffixes
        has_number = len(suffixes) != len(self.filename.suffixes)
        current_number = 0 if not has_number else int(suffixes[-1][1:])
        new_number = current_number + 1

        # Rename with new number suffix
        if has_number:
            suffixes.pop()
        suffixes.append(f".{new_number}")
        stem = file.name.split(".", maxsplit=1)[0]
        new_name = stem + "".join(suffixes)
        print(f"Log file renamed: {file.name} -> {new_name}")
        file = file.rename(file.with_name(new_name))

        # Remove older files
        if new_number > self.backup_count:
            print(f"Log file deleted: {file.name}")
            file.unlink()
            return

    def rotate(self) -> None:
        """Rotate the numbered suffix on the log files and remove old ones"""
        files = list(self.filename.parent.iterdir())
        files.sort(key=lambda file: file.name, reverse=True)
        for file in files:
            self.rotate_file(file)

    def __init__(self, filename: PathLike, backup_count: int = 2) -> None:
        self.filename = Path(filename)
        self.backup_count = backup_count
        self.create_dir()
        self.rotate()
        self.log_file = lzma.open(
            self.filename, "at", format=FORMAT_XZ, preset=PRESET_DEFAULT
        )
        super().__init__(self.log_file)

    def close(self) -> None:
        self.log_file.close()
        super().close()
