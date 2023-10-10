import logging
import os
import subprocess
from shlex import quote

from cartridges import shared


def run_executable(executable) -> None:
    args = (
        "flatpak-spawn --host /bin/sh -c " + quote(executable)  # Flatpak
        if os.getenv("FLATPAK_ID") == shared.APP_ID
        else executable  # Others
    )

    logging.info("Launching `%s`", str(args))
    # pylint: disable=consider-using-with
    subprocess.Popen(
        args,
        cwd=shared.home,
        shell=True,
        start_new_session=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,  # type: ignore
    )
