import logging
import logging.config as logging_dot_config
import os

from src import shared


def setup_logging():
    """Intitate the app's logging"""

    # Prepare the log file
    log_dir = shared.data_dir / "cartridges" / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "cartridges.log"
    log_file_max_size_bytes = 8 * 10**6  # 8 MB

    # Define log levels
    profile_app_log_level = "DEBUG" if shared.PROFILE == "development" else "INFO"
    profile_lib_log_level = "INFO" if shared.PROFILE == "development" else "WARNING"
    app_log_level = os.environ.get("LOGLEVEL", profile_app_log_level).upper()
    lib_log_level = os.environ.get("LIBLOGLEVEL", profile_lib_log_level).upper()

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
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "file_formatter",
                "level": "DEBUG",
                "filename": log_file_path,
                "maxBytes": log_file_max_size_bytes,
                "backupCount": 1,
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

    # Inform of the logging behaviour
    logging.info("Logging profile: %s", shared.PROFILE)
    logging.info("Console logging level for application: %s", app_log_level)
    logging.info("Console logging level for libraries: %s", lib_log_level)
    logging.info("Use env vars LOGLEVEL, LIBLOGLEVEL to override")
    logging.info("All message levels are written to the log file")
