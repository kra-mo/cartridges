import logging
import logging.config as logging_dot_config
import os
import subprocess
import sys

from src import shared  # pylint: disable=no-name-in-module


def setup_logging():
    """Intitate the app's logging"""

    is_dev = shared.PROFILE == "development"
    profile_app_log_level = "DEBUG" if is_dev else "INFO"
    profile_lib_log_level = "INFO" if is_dev else "WARNING"
    app_log_level = os.environ.get("LOGLEVEL", profile_app_log_level).upper()
    lib_log_level = os.environ.get("LIBLOGLEVEL", profile_lib_log_level).upper()

    log_filename = shared.cache_dir / "cartridges" / "logs" / "cartridges.log.xz"

    config = {
        "version": 1,
        "formatters": {
            "file_formatter": {
                "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
            },
            "console_formatter": {
                "format": "%(name)s %(levelname)s - %(message)s",
                "class": "src.logging.color_log_formatter.ColorLogFormatter",
            },
        },
        "handlers": {
            "file_handler": {
                "class": "src.logging.session_file_handler.SessionFileHandler",
                "formatter": "file_formatter",
                "level": "DEBUG",
                "filename": log_filename,
                "backup_count": 3,
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
                "level": "NOTSET",
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


def log_system_info():
    """Log system debug information"""

    logging.debug("Starting %s v%s (%s)", shared.APP_ID, shared.VERSION, shared.PROFILE)
    logging.debug("System: %s", sys.platform)
    logging.debug("Python version: %s", sys.version)
    if os.getenv("FLATPAK_ID"):
        process = subprocess.run(
            ("flatpak-spawn", "--host", "flatpak", "--version"),
            capture_output=True,
            encoding="utf-8",
            check=False,
        )
        logging.debug("Flatpak version: %s", process.stdout.rstrip())
    if os.name == "posix":
        uname = os.uname()
        logging.debug("Uname info:")
        logging.debug("\tsysname: %s", uname.sysname)
        logging.debug("\trelease: %s", uname.release)
        logging.debug("\tversion: %s", uname.version)
        logging.debug("\tmachine: %s", uname.machine)
    logging.debug("-" * 80)
