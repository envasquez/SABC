import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Tuple

from core.helpers.logging.formatters import get_console_formatter, get_file_formatter


def create_handlers(
    log_dir: Path,
    log_level: int,
    max_bytes: int,
    backup_count: int,
) -> Tuple[
    logging.StreamHandler,
    logging.handlers.RotatingFileHandler,
    logging.handlers.RotatingFileHandler,
    logging.handlers.RotatingFileHandler,
]:
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    app_handler = logging.handlers.RotatingFileHandler(
        log_dir / "sabc.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    app_handler.setLevel(log_level)

    security_handler = logging.handlers.RotatingFileHandler(
        log_dir / "security.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    security_handler.setLevel(logging.INFO)

    error_handler = logging.handlers.RotatingFileHandler(
        log_dir / "error.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
    )
    error_handler.setLevel(logging.ERROR)
    return console_handler, app_handler, security_handler, error_handler


def configure_handler_formatters(
    console_handler: logging.StreamHandler,
    app_handler: logging.handlers.RotatingFileHandler,
    security_handler: logging.handlers.RotatingFileHandler,
    error_handler: logging.handlers.RotatingFileHandler,
    json_format: bool,
) -> None:
    console_formatter = get_console_formatter(json_format)
    file_formatter = get_file_formatter(json_format)
    console_handler.setFormatter(console_formatter)
    app_handler.setFormatter(file_formatter)
    security_handler.setFormatter(file_formatter)
    error_handler.setFormatter(file_formatter)
