from glob import escape
from pathlib import Path
from shutil import copyfile

from gi.repository import GLib


def copy_db(original_path: Path) -> Path:
    """
    Copy a sqlite database to a cache dir and return its new path.
    The caller in in charge of deleting the returned path's parent dir.
    """
    tmp = Path(GLib.Dir.make_tmp())
    for file in original_path.parent.glob(f"{escape(original_path.name)}*"):
        copy = tmp / file.name
        copyfile(str(file), str(copy))
    return tmp / original_path.name
