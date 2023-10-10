# session_file_handler.py
#
# Copyright 2023 Geoffrey Coulaud
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: GPL-3.0-or-later

import lzma
from io import TextIOWrapper
from logging import StreamHandler
from lzma import FORMAT_XZ, PRESET_DEFAULT
from os import PathLike
from pathlib import Path
from typing import Optional

from cartridges import shared


class SessionFileHandler(StreamHandler):
    """
    A logging handler that writes to a new file on every app restart.
    The files are compressed and older sessions logs are kept up to a small limit.
    """

    NUMBER_SUFFIX_POSITION = 1

    backup_count: int
    filename: Path
    log_file: Optional[TextIOWrapper] = None

    def create_dir(self) -> None:
        """Create the log dir if needed"""
        self.filename.parent.mkdir(exist_ok=True, parents=True)

    def path_is_logfile(self, path: Path) -> bool:
        return path.is_file() and path.name.startswith(self.filename.stem)

    def path_has_number(self, path: Path) -> bool:
        try:
            int(path.suffixes[self.NUMBER_SUFFIX_POSITION][1:])
        except (ValueError, IndexError):
            return False
        return True

    def get_path_number(self, path: Path) -> int:
        """Get the number extension in the filename as an int"""
        suffixes = path.suffixes
        number = (
            0
            if not self.path_has_number(path)
            else int(suffixes[self.NUMBER_SUFFIX_POSITION][1:])
        )
        return number

    def set_path_number(self, path: Path, number: int) -> str:
        """Set or add the number extension in the filename"""
        suffixes = path.suffixes
        if self.path_has_number(path):
            suffixes.pop(self.NUMBER_SUFFIX_POSITION)
        suffixes.insert(self.NUMBER_SUFFIX_POSITION, f".{number}")
        stem = path.name.split(".", maxsplit=1)[0]
        new_name = stem + "".join(suffixes)
        return new_name

    def file_sort_key(self, path: Path) -> int:
        """Key function used to sort files"""
        return self.get_path_number(path) if self.path_has_number(path) else 0

    def get_logfiles(self) -> list[Path]:
        """Get the log files"""
        logfiles = list(filter(self.path_is_logfile, self.filename.parent.iterdir()))
        logfiles.sort(key=self.file_sort_key, reverse=True)
        return logfiles

    def rotate_file(self, path: Path) -> None:
        """Rotate a file's number suffix and remove it if it's too old"""

        # If uncompressed, compress
        if not path.name.endswith(".xz"):
            try:
                with open(path, "r", encoding="utf-8") as original_file:
                    original_data = original_file.read()
            except UnicodeDecodeError:
                # If the file is corrupted, throw it away
                path.unlink()
                return

            # Compress the file
            compressed_path = path.with_suffix(path.suffix + ".xz")
            with lzma.open(
                compressed_path,
                "wt",
                format=FORMAT_XZ,
                preset=PRESET_DEFAULT,
                encoding="utf-8",
            ) as lzma_file:
                lzma_file.write(original_data)
            path.unlink()
            path = compressed_path

        # Rename with new number suffix
        new_number = self.get_path_number(path) + 1
        new_path_name = self.set_path_number(path, new_number)
        path = path.rename(path.with_name(new_path_name))

        # Remove older files
        if new_number > self.backup_count:
            path.unlink()
            return

    def rotate(self) -> None:
        """Rotate the numbered suffix on the log files and remove old ones"""
        for path in self.get_logfiles():
            self.rotate_file(path)

    def __init__(self, filename: PathLike, backup_count: int = 2) -> None:
        self.filename = Path(filename)
        self.backup_count = backup_count
        self.create_dir()
        self.rotate()
        self.log_file = open(self.filename, "w", encoding="utf-8")
        shared.log_files = self.get_logfiles()
        super().__init__(self.log_file)

    def close(self) -> None:
        if self.log_file:
            self.log_file.close()
        super().close()
