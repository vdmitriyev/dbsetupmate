"""Logging setup.

Importing dbmate as a library must not touch the host application's logging, so
:func:`get_logger` only ever attaches a ``NullHandler``. The CLI opts into file
logging by calling :func:`configure_logging`.
"""

import logging
from typing import Optional

from dbmate.constants import LOG_FILE_NAME, LOGGER_NAME, app_log_level

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_logger(logger_name: Optional[str] = None) -> logging.Logger:
    """Returns the dbmate logger.

    Args:
        logger_name (str, optional): logger to fetch. Defaults to ``"dbmate"``.

    Returns:
        logging.Logger: a logger that discards records until
        :func:`configure_logging` is called
    """

    logger = logging.getLogger(logger_name or LOGGER_NAME)
    if not logger.handlers:
        logger.addHandler(logging.NullHandler())

    return logger


def configure_logging(level: Optional[str] = None, log_file: Optional[str] = None) -> logging.Logger:
    """Attaches a file handler to the dbmate logger.

    Called by the CLI. A library consumer should configure logging itself instead.

    Args:
        level (str, optional): log level name. Defaults to ``APP_LOG_LEVEL``, read now.
        log_file (str, optional): file to write to. Defaults to ``dbmate.log`` in the
            current working directory - not next to the installed package, which may
            well be read-only.

    Returns:
        logging.Logger: the configured logger. If the log file cannot be opened,
        logging stays disabled rather than failing the command.
    """

    logger = get_logger()
    logger.setLevel(level or app_log_level())

    log_file = log_file or LOG_FILE_NAME
    if any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        return logger

    try:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
    except OSError as ex:
        # An unwritable working directory must not stop the CLI from running.
        logger.debug("Could not open the log file %s: %s", log_file, ex)
        return logger

    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)

    return logger
