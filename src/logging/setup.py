import logging.config as logging_dot_config
import os
from datetime import datetime

from src import shared


def setup_logging():
    """Intitate the app's logging"""

    # Prepare log file
    log_dir = shared.data_dir / "cartridges" / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f'{datetime.now().isoformat(timespec="seconds")}.log'

    # Define log levels
    profile_main_log_level = "DEBUG" if shared.PROFILE == "development" else "WARNING"
    profile_lib_log_level = "INFO" if shared.PROFILE == "development" else "WARNING"
    main_log_level = os.environ.get("LOGLEVEL", profile_main_log_level).upper()
    lib_log_level = os.environ.get("LIBLOGLEVEL", profile_lib_log_level).upper()

    # Load config
    config = {
        "version": 1,
        "formatters": {
            "console_formatter": {
                "class": "src.logging.color_log_formatter.ColorLogFormatter",
                "format": "%(name)s %(levelname)s - %(message)s",
            },
            "file_formatter": {
                "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
            },
        },
        "handlers": {
            "main_console_handler": {
                "class": "logging.StreamHandler",
                "formatter": "console_formatter",
                "level": main_log_level,
            },
            "lib_console_handler": {
                "class": "logging.StreamHandler",
                "formatter": "console_formatter",
                "level": lib_log_level,
            },
            "file_handler": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "filename": str(log_file),
                "formatter": "file_formatter",
            },
        },
        "loggers": {
            "PIL": {"handlers": ["lib_console_handler", "file_handler"]},
            "urllib3": {"handlers": ["lib_console_handler", "file_handler"]},
            "root": {"handlers": ["main_console_handler", "file_handler"]},
        },
    }
    logging_dot_config.dictConfig(config)
