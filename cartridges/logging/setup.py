# setup.py
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

import logging
import logging.config as logging_dot_config
import os
import platform
import subprocess
import sys

from cartridges import shared


def setup_logging() -> None:
    """Intitate the app's logging"""

    is_dev = shared.PROFILE == "development"
    profile_app_log_level = "DEBUG" if is_dev else "INFO"
    profile_lib_log_level = "INFO" if is_dev else "WARNING"
    app_log_level = os.environ.get("LOGLEVEL", profile_app_log_level).upper()
    lib_log_level = os.environ.get("LIBLOGLEVEL", profile_lib_log_level).upper()

    log_filename = shared.cache_dir / "cartridges" / "logs" / "cartridges.log"

    config = {
        "version": 1,
        "formatters": {
            "file_formatter": {
                "format": "%(asctime)s - %(levelname)s: %(message)s",
                "datefmt": "%M:%S",
            },
            "console_formatter": {
                "format": "%(name)s %(levelname)s - %(message)s",
                "class": "cartridges.logging.color_log_formatter.ColorLogFormatter",
            },
        },
        "handlers": {
            "file_handler": {
                "class": "cartridges.logging.session_file_handler.SessionFileHandler",
                "formatter": "file_formatter",
                "level": "DEBUG",
                "filename": log_filename,
                "backup_count": 2,
            },
            "app_console_handler": {
                "class": "logging.StreamHandler",
                "formatter": "console_formatter",
                "level": app_log_level,
            },
            "lib_console_handler": {
                "class": "logging.StreamHandler",
                "formatter": "console_formatter",
                "level": lib_log_level,
            },
        },
        "loggers": {
            "PIL": {
                "handlers": ["lib_console_handler", "file_handler"],
                "propagate": False,
                "level": "WARNING",
            },
            "urllib3": {
                "handlers": ["lib_console_handler", "file_handler"],
                "propagate": False,
                "level": "NOTSET",
            },
        },
        "root": {
            "level": "NOTSET",
            "handlers": ["app_console_handler", "file_handler"],
        },
    }
    logging_dot_config.dictConfig(config)


def log_system_info() -> None:
    """Log system debug information"""

    logging.debug("Starting %s v%s (%s)", shared.APP_ID, shared.VERSION, shared.PROFILE)
    logging.debug("Python version: %s", sys.version)
    if os.getenv("FLATPAK_ID") == shared.APP_ID:
        process = subprocess.run(
            ("flatpak-spawn", "--host", "flatpak", "--version"),
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        logging.debug("Flatpak version: %s", process.stdout.rstrip())
    logging.debug("Platform: %s", platform.platform())
    if os.name == "posix":
        for key, value in platform.uname()._asdict().items():
            logging.debug("\t%s: %s", key.title(), value)
    logging.debug("─" * 37)
